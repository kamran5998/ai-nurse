"""
Automated Test Suite for Clinical PDF Processor and Orsini PDF Filler Engine.
"""

import os
import unittest
from pathlib import Path
import fitz

from ai_engine.pdf_processor import PDFProcessor
from ai_engine.pdf_filler import OrsiniPDFFiller


class TestPDFPipeline(unittest.TestCase):
    """Verifies PDF extraction, coordinate-based rendering, and 4-page output."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.sample_pdf = cls.project_root / "templates" / "orsini_adult_form_template.pdf"
        cls.blank_pdf = cls.project_root / "templates" / "orsini_blank_template.pdf"

    def test_pdf_processor_extraction(self):
        """PDFProcessor should parse drug name, pages, and metadata from template."""
        if not self.sample_pdf.exists():
            self.skipTest("Sample PDF template not found.")

        proc = PDFProcessor()
        data = proc.extract_from_pdf(self.sample_pdf)

        self.assertEqual(data["pages_count"], 4)
        self.assertIn("Evkeeza", data.get("drug_name", ""))
        self.assertIsInstance(data.get("vitals"), dict)
        self.assertTrue(len(data.get("raw_text", "")) > 100)

    def test_pdf_filler_generates_valid_4page_document(self):
        """OrsiniPDFFiller should output a valid 4-page PDF with filled clinical fields."""
        filler = OrsiniPDFFiller(template_path=self.blank_pdf if self.blank_pdf.exists() else self.sample_pdf)

        sample_record = {
            "patient_name": "Test Patient",
            "dob": "01/01/1980",
            "date": "10/04/2026",
            "time_in": "09:00 AM",
            "time_out": "11:30 AM",
            "drug_name": "Evkeeza 795mg",
            "vitals_bp": "118/74",
            "vitals_temperature": "98.4 F",
            "vitals_pulse": "72",
            "vitals_respiration": "16",
            "vitals_weight": "65.5 kg",
            "site_of_insertion": "Right forearm",
            "pump_brand_model": "Baxter Sigma Spectrum",
            "lot_number_1": "LOT-12345",
            "exp_date_1": "12/2027",
            "clinician_name_title": "Sarah Jenkins, RN, BSN",
            "clinician_signature": "Sarah Jenkins, RN",
        }

        pdf_bytes = filler.fill_form(sample_record)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 100000)

        # Inspect resulting PDF document with PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        self.assertEqual(len(doc), 4)

        # Page 1 should contain inserted patient name and drug
        p1_text = doc[0].get_text()
        self.assertIn("Test Patient", p1_text)
        self.assertIn("Evkeeza", p1_text)
        self.assertIn("118/74", p1_text)

        # Page 3 should contain inserted lot number
        p3_text = doc[2].get_text()
        self.assertIn("LOT-12345", p3_text)

        doc.close()

    def test_pdf_filler_preview_images(self):
        """OrsiniPDFFiller should generate 4 high-resolution preview images."""
        filler = OrsiniPDFFiller()
        sample_record = {"patient_name": "Preview Test"}
        pdf_bytes = filler.fill_form(sample_record)

        previews = filler.render_preview_images(pdf_bytes, dpi=72)
        self.assertEqual(len(previews), 4)
        for img_bytes in previews:
            self.assertGreater(len(img_bytes), 5000)


if __name__ == "__main__":
    unittest.main()
