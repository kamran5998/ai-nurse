import os
import unittest
from unittest.mock import MagicMock, patch
import json

from ai_engine.medical_nlp import (
    MedicalNLP,
    ORSINI_SCHEMA,
    PAGE1_SCHEMA,
    PAGE2_SCHEMA,
    PAGE3_SCHEMA,
    PAGE4_SCHEMA,
)
from ai_engine.note_generator import NoteGenerator
from ai_engine.document_processor import DocumentProcessor


class TestMedicalNLP(unittest.TestCase):
    def setUp(self):
        self.nlp = MedicalNLP()

    def test_schema_definitions(self):
        """Ensure schemas have correct types and union schema contains all page keys."""
        self.assertIn("vitals_bp", PAGE1_SCHEMA)
        self.assertIn("brand_catheter", PAGE2_SCHEMA)
        self.assertIn("infusion_table", PAGE3_SCHEMA)
        self.assertIsInstance(PAGE3_SCHEMA["infusion_table"], list)
        self.assertIn("clinician_name_title", PAGE4_SCHEMA)

        for key in PAGE1_SCHEMA:
            self.assertIn(key, ORSINI_SCHEMA)
        for key in PAGE2_SCHEMA:
            self.assertIn(key, ORSINI_SCHEMA)
        for key in PAGE3_SCHEMA:
            self.assertIn(key, ORSINI_SCHEMA)
        for key in PAGE4_SCHEMA:
            self.assertIn(key, ORSINI_SCHEMA)

    def test_abbreviation_expansion(self):
        """Check expansion of common infusion medical abbreviations."""
        raw = "pt has bp 130/85, hr 74, rr 18, and c/o sob on exertion"
        expanded = self.nlp.expand_abbreviations(raw)
        self.assertIn("blood pressure", expanded)
        self.assertIn("heart rate", expanded)
        self.assertIn("respiratory rate", expanded)
        self.assertIn("shortness of breath", expanded)

    def test_vitals_extraction(self):
        """Verify regex extraction of vital signs with standard abbreviations."""
        text = "Vitals: BP: 124/82, HR: 76 bpm, temp: 98.4 F, SpO2: 98%, RR: 16, Wt: 68.5 kg, pain: 2/10"
        vitals = self.nlp.extract_vitals(text)
        self.assertEqual(vitals.get("blood_pressure"), "124/82")
        self.assertEqual(vitals.get("heart_rate"), "76")
        self.assertEqual(vitals.get("temperature"), "98.4")
        self.assertEqual(vitals.get("spo2"), "98")
        self.assertEqual(vitals.get("respiratory_rate"), "16")
        self.assertEqual(vitals.get("weight"), "68.5")
        self.assertEqual(vitals.get("pain_scale"), "2")

    def test_vitals_extraction_expanded_terms(self):
        """Verify regex extraction with expanded words (e.g. blood pressure, respirations, weight)."""
        text = "Patient blood pressure 118/74, heart rate 72 bpm, temperature 98.6 F, oxygen saturation 99%, resp 16 breaths, weight 65 kg, pain 0/10"
        vitals = self.nlp.extract_vitals(text)
        self.assertEqual(vitals.get("blood_pressure"), "118/74")
        self.assertEqual(vitals.get("heart_rate"), "72")
        self.assertEqual(vitals.get("temperature"), "98.6")
        self.assertEqual(vitals.get("spo2"), "99")
        self.assertEqual(vitals.get("respiratory_rate"), "16")
        self.assertEqual(vitals.get("weight"), "65")
        self.assertEqual(vitals.get("pain_scale"), "0")

    def test_phi_scrubbing(self):
        """Verify HIPAA Safe Harbor scrub of identifiers."""
        text = "Patient SSN 123-45-6789, phone 555-123-4567, email nurse@clinic.com, DOB 12/04/1980, zip 90210"
        scrubbed = self.nlp.scrub_phi(text)
        self.assertNotIn("123-45-6789", scrubbed)
        self.assertIn("<SSN>", scrubbed)
        self.assertNotIn("555-123-4567", scrubbed)
        self.assertIn("<PHONE>", scrubbed)
        self.assertNotIn("nurse@clinic.com", scrubbed)
        self.assertIn("<EMAIL>", scrubbed)
        self.assertNotIn("12/04/1980", scrubbed)
        self.assertIn("<DATE>", scrubbed)
        self.assertNotIn("90210", scrubbed)
        self.assertIn("<ZIP>", scrubbed)

    def test_detect_page(self):
        """Verify detection heuristic for form pages."""
        self.assertEqual(self.nlp.detect_page("IV access placed in left arm, PICC line"), 2)
        self.assertEqual(self.nlp.detect_page("Lot number 89218, infusion rate 150 ml/hr"), 3)
        self.assertEqual(self.nlp.detect_page("Progress goals discussed with clinician"), 4)
        self.assertEqual(self.nlp.detect_page("Patient presents for routine infusion"), 1)


class TestNoteGenerator(unittest.TestCase):
    def test_missing_api_key_raises_error(self):
        """Should raise ValueError when GEMINI_API_KEY is unset."""
        with patch.dict("os.environ", {}, clear=True):
            gen = NoteGenerator(api_key=None)
            with self.assertRaises(ValueError) as ctx:
                gen.generate("Sample clinical text")
            self.assertIn("GEMINI_API_KEY is not set", str(ctx.exception))

    @patch("google.generativeai.GenerativeModel")
    def test_generate_with_mocked_llm(self, mock_model_cls):
        """Test NoteGenerator parsing Gemini LLM response into schema."""
        mock_instance = MagicMock()
        mock_model_cls.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "patient_name": "Jane Doe",
            "vitals_bp": "118/74",
            "vitals_pulse": "72",
            "vitals_respiration": "16",
            "alert": True
        })
        mock_instance.generate_content.return_value = mock_response

        gen = NoteGenerator(provider="gemini", api_key="test-gemini-key")
        result = gen.generate("Jane Doe presented with BP 118/74, pulse 72, RR 16, alert.")

        self.assertEqual(result["patient_name"], "Jane Doe")
        self.assertEqual(result["vitals_bp"], "118/74")
        self.assertEqual(result["vitals_pulse"], "72")
        self.assertTrue(result["alert"])
        # Defaults should be filled
        self.assertIn("infusion_table", result)
        self.assertIsInstance(result["infusion_table"], list)

    def test_generate_mock_simulation(self):
        """Test intelligent offline mock simulation without API key."""
        with patch.dict("os.environ", {}, clear=True):
            gen = NoteGenerator(api_key=None)
            result = gen.generate("Patient Robert Smith arrived with BP 122/80, pulse 68, IVIG infusion.", mock=True)
            self.assertEqual(result["patient_name"], "Robert Smith")
            self.assertEqual(result["vitals_bp"], "122/80")
            self.assertEqual(result["vitals_pulse"], "68")
            self.assertEqual(result["drug_name"], "IVIG")
            self.assertIn("vitals_flow_sheet", result)
            self.assertIsInstance(result["vitals_flow_sheet"], list)

    def test_generate_from_voice_mock(self):
        """Test voice transcription fallback when running without external API."""
        gen = NoteGenerator(provider="mock")
        sample_audio = "sample_nurse_voice.wav"
        if os.path.exists(sample_audio):
            result = gen.generate_from_voice(sample_audio)
            self.assertIn("_transcript", result)
            self.assertIn("patient_name", result)
            self.assertIn("vitals_bp", result)


class TestDocumentProcessor(unittest.TestCase):
    def test_invalid_file_extension(self):
        """DocumentProcessor should reject unsupported extensions."""
        proc = DocumentProcessor(api_key="mock-test-key")
        with self.assertRaises(ValueError) as ctx:
            proc.process_image("document.pdf")
        self.assertIn("Unsupported file type", str(ctx.exception))

    def test_missing_api_key_raises_error(self):
        """Should raise ValueError when GEMINI_API_KEY is unset."""
        with patch.dict("os.environ", {}, clear=True):
            proc = DocumentProcessor(api_key=None)
            with self.assertRaises(ValueError) as ctx:
                proc.process_image("page1.jpg")
            self.assertIn("GEMINI_API_KEY is not set", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
