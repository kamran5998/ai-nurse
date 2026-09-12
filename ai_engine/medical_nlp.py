import re
from typing import Optional

# ── Orsini Infusion Nursing Notes: Adult — complete field schema ──────────────

# Page 1 — Patient Info + Clinical Assessments
PAGE1_SCHEMA = {
    # Patient header
    "patient_name": "",
    "dob": "",
    "date": "",
    "time_in": "",
    "time_out": "",
    "drug_name": "",
    "parking": "",
    "mileage": "",

    # Pre-infusion vital signs
    "vitals_bp": "",
    "vitals_temperature": "",
    "vitals_pulse": "",
    "vitals_respiration": "",
    "vitals_weight": "",
    "vitals_pain_scale": "",
    "standard_precautions_maintained": False,

    # Medications
    "new_or_changed_medications": "",
    "medication_profile_updated": "",
    "medications_specified": "",
    "instructions_given": "",

    # Respiratory
    "lung_sounds": "",
    "rhonchi": False,
    "wheezes": False,
    "diminished": False,
    "absent": False,
    "respiratory_note": "",
    "cough": "",
    "hemoptysis_frequency_amount": "",
    "suction_secretions": "",
    "respiratory_status": "",
    "orthopnea": False,
    "dyspnea": False,
    "minimal_exertion": False,
    "with_moderate_exertion": False,
    "oxygen_lpm": "",
    "oxygen_as_needed": False,
    "oxygen_continuous": False,
    "stridor_retractions": "",

    # Pain assessment
    "pain_location": "",
    "pain_scale": "",
    "pain_acute": False,
    "pain_chronic": False,
    "pain_characteristics": "",
    "pain_alleviating_factors": "",
    "pain_effects": "",
    "pain_diversion": False,
    "pain_throbbing": False,
    "pain_other": "",

    # Cardiopulmonary
    "heart_sounds": "",
    "murmur_abnormal": "",
    "edema_pedal": False,
    "edema_right_ankle": False,
    "edema_left_ankle": False,
    "capillary_refill": "",
    "greater_than_2_seconds": False,
    "cramps": False,
    "claudication": False,
    "pain_localized": False,
    "pain_stabbing": False,
    "cardio_other": "",
    "associated_with_shortness_of_breath": False,
    "activity": "",
    "rest": False,
    "new_onset": False,
    "duration": "",

    # Neurological
    "alert": False,
    "oriented_to_person": False,
    "oriented_to_place": False,
    "oriented_to_time": False,
    "forgetful": False,
    "syncope": False,
    "disoriented": False,
    "headache": False,
    "unsteady_gait": False,
    "neuro_other": "",
    "pupils_perrla": False,
    "pupils_right": False,
    "pupils_left": False,
    "pupils_both": False,
    "hearing": False,
    "visual": False,
    "decreased_sensitivity": False,
    "tremors": False,
    "numbness": False,
    "tingling_depressed": False,
    "flat_affect": False,
    "difficulty_coping": False,
    "angry": False,
    "withdrawn": False,
    "vertigo_ataxia_falls": "",
    "neuro_notes": "",

    # Musculoskeletal
    "weakness": False,
    "balance_gait_abnormal": False,
    "limited_mobility_rom": False,
    "bedbound": False,
    "chairbound": False,
    "contracture": False,
    "paralysis_assistive_device": False,
    "fall_precaution_maintained": False,
    "musculoskeletal_notes": "",

    # Skin
    "no_deficit": False,
    "rash": False,
    "flushed": False,
    "jaundice": False,

    # Gastrointestinal
    "bowel_sounds": "",
    "hyperactive": False,
    "hypoactive": False,
    "gi_quadrants": "",
    "gastrostomy": False,
    "ileostomy": False,
    "tube_feeding_type_amount": "",
    "good": False,
    "fair": False,
    "poor": False,
    "difficulty_swallowing": False,
    "replacement_diet": False,
    "new_ostomy": False,
    "regular_diet": False,
    "npo": False,
    "ileostomy_colostomy": False,
    "impaction": False,
    "constipation": False,
    "impaction_diarrhea": False,
    "abdominal_pain": False,
    "distension_flatulence": False,
    "nausea_vomiting": False,
    "anorexia": False,
    "ng_tube": False,
}

# Page 2 — IV Access + Pump + Medications + Labs
PAGE2_SCHEMA = {
    "date_of_placement": "",
    "type_of_access": "",
    "other_access": "",
    "brand_catheter": "",
    "lumen": "",
    "french_size": "",
    "external_internal_length": "",
    "site_of_insertion": "",
    "site_condition": "",
    "current_dressing_intact": "",
    "current_dressing_type": "",
    "current_dressing_performed": "",
    "site_cleansed_with": "",
    "dressing_type": "",
    "extension_changed": "",
    "gauge_tape": "",
    "biopatch": "",
    "brand_gauge": "",
    "complications": "",
    "catheter_discounted": "",
    "reason_for_removal": "",
    "therapy_completed": False,
    "vein_thrombosis": False,
    "damaged_catheter": False,
    "systemic_infection": False,
    "access_device_flushed": "",
    "blood_return": "",
    "huber_needle_size_length": "",
    "attempt_number": "",
    "iv_comments": "",

    # Pump
    "pump_brand_model": "",
    "pump_program_verified": "",
    "pump_settings_verified_with_label": "",
    "pump_settings_changed": "",

    # Medications
    "pre_medication_given_by": "",
    "therapy_admin_by": "",
    "saline_flush_ml": "",
    "pre_infusion_other": "",
    "heparin_units_ml": "",
    "flush_ns_ml": "",
    "anaphylactic_kit_expiration": "",
    "epi_pen_expiration": "",

    # Labs
    "labs_drawn": "",
    "labs_specify": "",
    "labs_drawn_from": "",
    "access_device_flushed_with_ns_ml": "",
    "heparin_units_ml_lab": "",
    "name_of_lab_blood_taken_to": "",
}

# Page 3 — Patient/Caregiver Teaching + Solution/Medication Table + Vitals Flow Sheet
PAGE3_SCHEMA = {
    "lot_number_1": "",
    "exp_date_1": "",
    "lot_number_2": "",
    "exp_date_2": "",
    "lot_number_3": "",
    "exp_date_3": "",
    "lot_number_4": "",
    "exp_date_4": "",
    "lot_number_5": "",
    "exp_date_5": "",
    "lot_number_6": "",
    "exp_date_6": "",

    # Solution/Medication infusion table (list of dicts)
    "infusion_table": [],
    # Each entry: {"solution_medication": "", "amount": "", "time_started": "",
    #              "time_completed": "", "amount_infused": ""}

    # Vitals flow sheet (list of dicts)
    "vitals_flow_sheet": [],
    # Each entry: {"time": "", "pulse": "", "resp_rate": "", "temp": "",
    #              "bp": "", "o2_percent": "", "infusion_rate": "", "comments": ""}

    "narrative": "",
    "pharmacy_notes": "",
}

# Page 4 — Care Coordination + Teaching + Signatures
PAGE4_SCHEMA = {
    "case_conference_with": "",
    "other_summary": "",
    "clinician_name_title": "",
    "clinician_signature": "",
    "clinician_signature_date": "",
    "patient_caregiver_signature": "",
    "patient_caregiver_signature_date": "",

    # Progress / Teaching (second section on page 4)
    "progress_goals": "",
    "teaching_tool_used_given": "",
    "instructed": False,
    "pt_cg_verbalized_understanding": False,
    "pt_cg_return_demo": False,
    "care_coordination_with": "",
    "care_coordination_name": "",
    "care_coordination_regarding": "",
    "physician_contacted_re": "",
    "physician_contact_date_time": "",
    "order_changes": "",
    "plan_for_next_visit": "",
    "discharge_planning": "",
}

# Full combined schema
ORSINI_SCHEMA = {**PAGE1_SCHEMA, **PAGE2_SCHEMA, **PAGE3_SCHEMA, **PAGE4_SCHEMA}

# ---------------------------------------------------------------------------
# Clinical Abbreviation Normalization Dictionary
# Maps common infusion nursing shorthand to standardized clinical terminology.
# ---------------------------------------------------------------------------
ABBREVIATIONS: dict[str, str] = {
    "bp": "blood pressure",
    "hr": "heart rate",
    "rr": "respiratory rate",
    "temp": "temperature",
    "spo2": "oxygen saturation",
    "prn": "as needed",
    "bid": "twice daily",
    "tid": "three times daily",
    "qid": "four times daily",
    "po": "by mouth",
    "iv": "intravenous",
    "im": "intramuscular",
    "sob": "shortness of breath",
    "cp": "chest pain",
    "hx": "history",
    "dx": "diagnosis",
    "rx": "prescription",
    "sx": "symptoms",
    "npo": "nothing by mouth",
    "piv": "peripheral IV",
    "ns": "normal saline",
    "picc": "peripherally inserted central catheter",
    "adl": "activities of daily living",
    "perrla": "pupils equal round reactive to light",
    "wnl": "within normal limits",
    "lpm": "liters per minute",
}

# ---------------------------------------------------------------------------
# HIPAA Safe Harbor De-identification Rules (45 CFR § 164.514(b)(2))
# Pre-compiled regular expressions for high-throughput identifier scrubbing.
# ---------------------------------------------------------------------------
_RAW_PHI_RULES = [
    (r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>"),
    (r"\b\d{10,}\b", "<ID>"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>"),
    (r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "<PHONE>"),
    (r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", "<DATE>"),
    (r"\b\d{5}(?:-\d{4})?\b", "<ZIP>"),
]

# Pre-compile for O(1) loop iteration without re-parsing regex AST
_COMPILED_PHI_PATTERNS = [
    (re.compile(pattern), placeholder)
    for pattern, placeholder in _RAW_PHI_RULES
]

# Pre-compiled vital signs extractors supporting both shorthand and natural language
_COMPILED_VITALS_PATTERNS = {
    "blood_pressure": re.compile(r"(?:bp|blood\s*pressure)[:\s]+(\d{2,3}/\d{2,3})", re.IGNORECASE),
    "heart_rate": re.compile(r"(?:hr|pulse|heart\s*rate)[:\s]+(\d{2,3})\s*(?:bpm)?", re.IGNORECASE),
    "temperature": re.compile(r"(?:temp|temperature)[:\s]+([\d.]+)\s*(?:f|c)?", re.IGNORECASE),
    "spo2": re.compile(r"(?:spo2|o2\s*sat|oxygen\s*saturation)[:\s]+(\d{2,3})\s*%?", re.IGNORECASE),
    "respiratory_rate": re.compile(r"(?:rr|resp(?:irations?|iratory\s*rate)?)[:\s]+(\d{2,3})\s*(?:breaths)?", re.IGNORECASE),
    "weight": re.compile(r"(?:wt|weight)[:\s]+([\d.]+)\s*(?:kg|lbs?)?", re.IGNORECASE),
    "pain_scale": re.compile(r"pain[:\s]+(\d{1,2})(?:/10)?", re.IGNORECASE),
}


class MedicalNLP:
    """
    Clinical Natural Language Processing engine tailored for Infusion Nursing Notes.

    Provides high-performance text normalization, regex-driven vitals extraction,
    HIPAA Safe Harbor PHI scrubbing, and Orsini form page classification.
    """

    def expand_abbreviations(self, text: str) -> str:
        """
        Expands clinical shorthand and nursing acronyms into full medical terms.

        Args:
            text: Raw input string from nurse speech-to-text or free-form notes.

        Returns:
            Normalized clinical narrative with standardized medical terms.
        """
        words = text.split()
        expanded_tokens = []
        for word in words:
            # Strip trailing punctuation for dictionary match while preserving word context
            clean_token = word.lower().rstrip(".,:;")
            if clean_token in ABBREVIATIONS:
                expanded_word = ABBREVIATIONS[clean_token]
                # Re-attach trailing punctuation if present
                if word[-1] in ".,:;":
                    expanded_word += word[-1]
                expanded_tokens.append(expanded_word)
            else:
                expanded_tokens.append(word)

        return " ".join(expanded_tokens)

    def scrub_phi(self, text: str) -> str:
        """
        Redacts Protected Health Information (PHI) to satisfy HIPAA Safe Harbor rules.
        Replaces sensitive identifiers (SSN, phone, email, date, zip) with anonymized tokens.

        Args:
            text: Raw clinical text containing potential patient identifiers.

        Returns:
            De-identified text safe for storage, analytics, or cloud LLM submission.
        """
        sanitized_text = text
        for compiled_pattern, placeholder in _COMPILED_PHI_PATTERNS:
            sanitized_text = compiled_pattern.sub(placeholder, sanitized_text)
        return sanitized_text

    def extract_vitals(self, text: str) -> dict[str, str]:
        """
        Extracts pre-infusion vital signs using optimized regular expressions.
        Handles both shorthand (BP, HR, RR, SpO2, Wt) and expanded clinical vocabulary.

        Args:
            text: Raw or normalized clinical text.

        Returns:
            Dictionary of identified vital sign values keyed by physiological measure.
        """
        extracted_vitals: dict[str, str] = {}
        for vital_key, compiled_regex in _COMPILED_VITALS_PATTERNS.items():
            match = compiled_regex.search(text)
            if match:
                extracted_vitals[vital_key] = match.group(1)
        return extracted_vitals

    def detect_page(self, text: str) -> Optional[int]:
        """
        Classifies clinical narrative into the most relevant Orsini form page (1-4)
        based on domain-specific keyword clusters.

        Args:
            text: Clinical note snippet.

        Returns:
            Page number (1: Vitals/Assessment, 2: IV Access/Pump, 3: Flow Sheet, 4: Care/Discharge).
        """
        normalized_text = text.lower()
        if any(keyword in normalized_text for keyword in ["iv access", "pump", "brand catheter", "picc"]):
            return 2
        if any(keyword in normalized_text for keyword in ["lot number", "infusion rate", "time started", "narrative"]):
            return 3
        if any(keyword in normalized_text for keyword in ["progress goals", "teaching tool", "discharge planning", "clinician"]):
            return 4
        return 1

