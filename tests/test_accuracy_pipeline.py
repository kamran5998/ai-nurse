import unittest
from ai_engine import NoteGenerator, OrsiniPDFFiller, merge_clinical_data

class TestAccuracyPipeline(unittest.TestCase):
    def test_voice_to_blank_pdf_end_to_end(self):
        gen = NoteGenerator(provider='mock')
        input_text = (
            "Patient Jane smite (DOB April 15th, 1975) presented on 09/11/2025 for scheduled IVIG 10g infusion. "
            "Pre-infusion vitals: BP 118/74, pulse 72, temperature 98.4 F, resp 16, weight 65.5 kg, pain 0/10. "
            "20-gauge PIV placed in right forearm, 2 attempts, brisk blood return. "
            "Started at 09:00 AM, ended at 11:30 AM via Baxter pump. Lot 99281726, exp 05/26. Flush 10 mL NS. "
            "Nurse Sarah Connor RN."
        )

        note = gen.generate_mock(input_text)
        self.assertEqual(note['patient_name'], 'Jane Smite')
        self.assertEqual(note['dob'], '04/15/1975')
        self.assertEqual(note['date'], '09/11/2025')
        self.assertEqual(note['drug_name'], 'IVIG')
        self.assertEqual(note['vitals_bp'], '118/74')
        self.assertEqual(note['brand_gauge'], 'Angiocath 20G')
        self.assertEqual(note['attempt_number'], '2')
        self.assertEqual(note['pump_brand_model'], 'Baxter Pump')
        self.assertEqual(note['lot_number_1'], '99281726')
        self.assertEqual(note['exp_date_1'], '05/26')
        self.assertEqual(note['clinician_signature'], 'Sarah Connor RN')
        self.assertEqual(len(note['vitals_flow_sheet']), 6)

        filler = OrsiniPDFFiller('templates/orsini_blank_template.pdf')
        pdf_bytes = filler.fill_form(note)
        self.assertGreater(len(pdf_bytes), 100000)
        previews = filler.render_preview_images(pdf_bytes)
        self.assertEqual(len(previews), 4)

    def test_zero_fallback_when_only_patient_name_provided(self):
        """Verifies that dictating ONLY patient name produces NO fallback mock data anywhere."""
        import fitz
        gen = NoteGenerator(provider='mock')
        note = gen.generate_mock("patient name john abraham")

        # Clinical note verification: only patient name is present
        self.assertEqual(note['patient_name'], 'John Abraham')
        self.assertEqual(note['drug_name'], '')
        self.assertEqual(note['vitals_bp'], '')
        self.assertEqual(note['pump_brand_model'], '')
        self.assertEqual(note['infusion_table'], [])
        self.assertEqual(note['vitals_flow_sheet'], [])
        self.assertEqual(note['clinician_signature'], '')
        self.assertFalse(note['standard_precautions_maintained'])

        # Merger verification: no default fallback injection
        merged = merge_clinical_data({}, note)
        self.assertEqual(merged['patient_name'], 'John Abraham')
        self.assertEqual(merged['drug_name'], '')
        self.assertEqual(merged['vitals_bp'], '')
        self.assertEqual(merged['infusion_table'], [])

        # PDF Filler verification: only patient name is stamped, no fake data
        filler = OrsiniPDFFiller('templates/orsini_blank_template.pdf')
        pdf_bytes = filler.fill_form(note)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        all_text = " ".join(page.get_text() for page in doc)
        self.assertIn("John Abraham", all_text)
        self.assertNotIn("Evkeeza", all_text)
        self.assertNotIn("118/74", all_text)
        self.assertNotIn("107/66", all_text)
        self.assertNotIn("Baxter", all_text)
        self.assertNotIn("Curlin", all_text)
        self.assertNotIn("Hilario", all_text)
        self.assertNotIn("Jane Doe", all_text)
        doc.close()

if __name__ == '__main__':
    unittest.main()
