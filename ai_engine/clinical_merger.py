"""
Clinical Data Merger for Orsini Infusion Nursing Documentation.
Intelligently merges pre-existing PDF baseline information with real-time nurse voice/text dictation,
giving authoritative 100% precedence to nurse spoken observations.
"""

from __future__ import annotations

import copy
from typing import Any
from .medical_nlp import ORSINI_SCHEMA


def merge_clinical_data(
    pdf_baseline: dict[str, Any],
    nurse_updates: dict[str, Any],
) -> dict[str, Any]:
    """
    Combines baseline PDF records with nurse spoken/typed updates.

    Priority Rules:
    1. Nurse spoken/typed observations take 100% precedence for any documented field.
    2. If a field was not mentioned by the nurse, the value from the uploaded PDF is preserved.
    3. If neither specified the field, standard clinical defaults are applied.

    Args:
        pdf_baseline: Dictionary of fields extracted from uploaded PDF.
        nurse_updates: Dictionary of fields extracted from nurse dictation.

    Returns:
        Consolidated dictionary conforming to ORSINI_SCHEMA.
    """
    merged = copy.deepcopy(ORSINI_SCHEMA)

    # 1. First populate from PDF baseline
    for k, v in pdf_baseline.items():
        if k in merged and v not in (None, "", False, [], {}):
            merged[k] = v

    # 2. Apply nurse updates with 100% priority
    for k, v in nurse_updates.items():
        if k in merged and v not in (None, "", False, [], {}):
            merged[k] = v

    # 3. Specific clinical field synchronizations
    # Ensure patient name is title cased and valid if present
    p_name = nurse_updates.get("patient_name") or pdf_baseline.get("patient_name") or ""
    if p_name and str(p_name).strip().lower() not in ("name", "the", "a", "unknown"):
        merged["patient_name"] = str(p_name).strip().title()
    else:
        merged["patient_name"] = ""

    # Drug name
    merged["drug_name"] = nurse_updates.get("drug_name") or pdf_baseline.get("drug_name") or ""

    # Dates and times
    merged["date"] = nurse_updates.get("date") or pdf_baseline.get("date") or ""
    merged["dob"] = nurse_updates.get("dob") or pdf_baseline.get("dob") or ""
    merged["time_in"] = nurse_updates.get("time_in") or pdf_baseline.get("time_in") or ""
    merged["time_out"] = nurse_updates.get("time_out") or pdf_baseline.get("time_out") or ""

    # Vitals
    merged["vitals_bp"] = nurse_updates.get("vitals_bp") or pdf_baseline.get("vitals_bp") or ""
    merged["vitals_pulse"] = nurse_updates.get("vitals_pulse") or pdf_baseline.get("vitals_pulse") or ""
    merged["vitals_temperature"] = nurse_updates.get("vitals_temperature") or pdf_baseline.get("vitals_temperature") or ""
    merged["vitals_respiration"] = nurse_updates.get("vitals_respiration") or pdf_baseline.get("vitals_respiration") or ""
    merged["vitals_pain_scale"] = nurse_updates.get("vitals_pain_scale") or pdf_baseline.get("vitals_pain_scale") or ""

    # Catheter & Pump
    merged["site_of_insertion"] = nurse_updates.get("site_of_insertion") or pdf_baseline.get("site_of_insertion") or ""
    merged["brand_gauge"] = nurse_updates.get("brand_gauge") or pdf_baseline.get("brand_gauge") or ""
    merged["pump_brand_model"] = nurse_updates.get("pump_brand_model") or pdf_baseline.get("pump_brand_model") or ""
    merged["saline_flush_ml"] = nurse_updates.get("saline_flush_ml") or pdf_baseline.get("saline_flush_ml") or ""

    # Lots & Expiration
    merged["lot_number_1"] = nurse_updates.get("lot_number_1") or pdf_baseline.get("lot_number_1") or ""
    merged["exp_date_1"] = nurse_updates.get("exp_date_1") or pdf_baseline.get("exp_date_1") or ""

    # Signatures
    nurse_sig = (nurse_updates.get("clinician_signature") or pdf_baseline.get("clinician_signature") or "").strip()
    merged["clinician_signature"] = nurse_sig
    if nurse_sig:
        merged["clinician_name_title"] = nurse_sig if "BSN" in nurse_sig else f"{nurse_sig}, BSN"
        merged["clinician_signature_date"] = merged.get("date", "")
    else:
        merged["clinician_name_title"] = ""
        merged["clinician_signature_date"] = ""

    # Flow sheet & Infusion table synchronization
    if nurse_updates.get("vitals_flow_sheet"):
        merged["vitals_flow_sheet"] = nurse_updates["vitals_flow_sheet"]
    elif pdf_baseline.get("vitals_flow_sheet"):
        merged["vitals_flow_sheet"] = pdf_baseline["vitals_flow_sheet"]
    else:
        merged["vitals_flow_sheet"] = []

    if nurse_updates.get("infusion_table"):
        merged["infusion_table"] = nurse_updates["infusion_table"]
    elif pdf_baseline.get("infusion_table"):
        merged["infusion_table"] = pdf_baseline["infusion_table"]
    else:
        merged["infusion_table"] = []

    return merged
