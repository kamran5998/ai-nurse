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

    def test_patient_name_only_leaves_all_other_fields_blank(self):
        import fitz
        gen = NoteGenerator(provider='mock')
        note = gen.generate('Patient name John Abraham', mock=True)

        self.assertEqual(note.get('patient_name'), 'John Abraham')
        self.assertEqual(note.get('dob', ''), '')
        self.assertEqual(note.get('date', ''), '')
        self.assertEqual(note.get('drug_name', ''), '')
        self.assertEqual(note.get('vitals_bp', ''), '')
        self.assertEqual(note.get('pump_brand_model', ''), '')
        self.assertEqual(note.get('lot_number_1', ''), '')
        self.assertEqual(note.get('clinician_signature', ''), '')

        filler = OrsiniPDFFiller('templates/orsini_blank_template.pdf')
        pdf_bytes = filler.fill_form(note)

        doc = fitz.open(stream=pdf_bytes, filetype='pdf')
        # Patient name must appear
        self.assertIn('John Abraham', doc[0].get_text())
        # Unmentioned data must NOT appear
        self.assertNotIn('Jane Doe', doc[0].get_text())
        self.assertNotIn('Evkeeza', doc[0].get_text())
        self.assertNotIn('118/74', doc[0].get_text())
        self.assertNotIn('107/66', doc[0].get_text())
        self.assertNotIn('Curlin', doc[1].get_text())
        self.assertNotIn('83242000007', doc[2].get_text())
        self.assertNotIn('Hilario castillo', doc[3].get_text())
        doc.close()


if __name__ == '__main__':
    unittest.main()
