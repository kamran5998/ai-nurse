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
    p_name = nurse_updates.get("patient_name") or pdf_baseline.get("patient_name")
    if p_name and str(p_name).strip().lower() not in ("name", "the", "a", "unknown", ""):
        merged["patient_name"] = str(p_name).strip().title()

    # Drug name
    drug = nurse_updates.get("drug_name") or pdf_baseline.get("drug_name") or ""
    if drug:
        merged["drug_name"] = drug

    # Dates and times
    if nurse_updates.get("date") or pdf_baseline.get("date"):
        merged["date"] = nurse_updates.get("date") or pdf_baseline.get("date")
    if nurse_updates.get("dob") or pdf_baseline.get("dob"):
        merged["dob"] = nurse_updates.get("dob") or pdf_baseline.get("dob")
    if nurse_updates.get("time_in") or pdf_baseline.get("time_in"):
        merged["time_in"] = nurse_updates.get("time_in") or pdf_baseline.get("time_in")
    if nurse_updates.get("time_out") or pdf_baseline.get("time_out"):
        merged["time_out"] = nurse_updates.get("time_out") or pdf_baseline.get("time_out")

    # Vitals
    for v_field in ("vitals_bp", "vitals_pulse", "vitals_temperature", "vitals_respiration", "vitals_pain_scale", "vitals_weight", "pain_location"):
        val = nurse_updates.get(v_field) or pdf_baseline.get(v_field)
        if val:
            merged[v_field] = val

    # Catheter & Pump
    for c_field in ("site_of_insertion", "brand_gauge", "attempt_number", "site_condition", "pump_brand_model", "saline_flush_ml", "lot_number_1", "exp_date_1"):
        val = nurse_updates.get(c_field) or pdf_baseline.get(c_field)
        if val:
            merged[c_field] = val

    # Signatures
    nurse_sig = nurse_updates.get("clinician_signature") or pdf_baseline.get("clinician_signature") or ""
    if nurse_sig:
        merged["clinician_signature"] = nurse_sig
        merged["clinician_name_title"] = nurse_updates.get("clinician_name_title") or pdf_baseline.get("clinician_name_title") or (nurse_sig if "BSN" in nurse_sig else f"{nurse_sig}, BSN")
        merged["clinician_signature_date"] = merged.get("date", "")

    # Flow sheet & Infusion table synchronization
    if nurse_updates.get("vitals_flow_sheet"):
        merged["vitals_flow_sheet"] = nurse_updates["vitals_flow_sheet"]
    elif pdf_baseline.get("vitals_flow_sheet"):
        merged["vitals_flow_sheet"] = pdf_baseline["vitals_flow_sheet"]

    if nurse_updates.get("infusion_table"):
        merged["infusion_table"] = nurse_updates["infusion_table"]
    elif pdf_baseline.get("infusion_table"):
        merged["infusion_table"] = pdf_baseline["infusion_table"]

    return merged
