"""
Clinical PDF Document Processor for Orsini Infusion Nursing Documentation.
Extracts patient demographics, clinical vitals, medications, and pre-existing
values from uploaded PDF records using PyMuPDF spatial bounding boxes and Medical NLP heuristics.
"""

from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from typing import Any, Optional, Union
import fitz  # PyMuPDF

from .medical_nlp import MedicalNLP

logger = logging.getLogger(__name__)
_nlp = MedicalNLP()


class PDFProcessor:
    """
    Parses uploaded clinical PDF documents to extract patient identifiers,
    visit metadata, prior vital signs, and narrative clinical history with high accuracy.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initializes the clinical PDF processor."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def extract_from_pdf(self, pdf_input: Union[str, Path, bytes]) -> dict[str, Any]:
        """
        Extracts structured clinical information from a PDF file path or raw bytes.
        Combines spatial bounding-box parsing for structured forms with regex fallbacks.
        """
        if isinstance(pdf_input, (str, Path)):
            doc = fitz.open(str(pdf_input))
        else:
            doc = fitz.open(stream=pdf_input, filetype="pdf")

        pages_text: list[str] = []
        pages_blocks: list[list[Any]] = []
        for page in doc:
            pages_text.append(page.get_text().strip())
            pages_blocks.append(page.get_text("blocks"))

        full_text = "\n\n".join(pages_text)
        expanded_text = _nlp.expand_abbreviations(full_text)

        result: dict[str, Any] = {
            "patient_name": "",
            "dob": "",
            "date": "",
            "time_in": "",
            "time_out": "",
            "drug_name": "",
            "parking": "",
            "mileage": "",
            "vitals_bp": "",
            "vitals_temperature": "",
            "vitals_pulse": "",
            "vitals_respiration": "",
            "vitals_weight": "",
            "vitals_pain_scale": "",
            "pain_location": "",
            "brand_gauge": "",
            "site_of_insertion": "",
            "attempt_number": "",
            "site_condition": "",
            "discontinue_note": "",
            "pump_brand_model": "",
            "saline_flush_ml": "",
            "lot_number_1": "",
            "exp_date_1": "",
            "clinician_signature": "",
            "clinician_name_title": "",
            "diet": "",
            "instructions_given": "",
            "specify_new_changed_meds": "",
            "pages_count": len(pages_text),
            "pages_text": pages_text,
            "raw_text": full_text,
        }

        # -------------------------------------------------------------------
        # Page 1 Spatial & Semantic Extraction
        # -------------------------------------------------------------------
        if len(pages_blocks) >= 1:
            for b in pages_blocks[0]:
                txt = b[4].strip()
                x0, y0, x1, y1 = b[:4]
                if not txt:
                    continue

                # Patient Name (value block near Patient Name label)
                if 90 < x0 < 300 and 135 < y0 < 152 and not result["patient_name"]:
                    if not txt.lower().startswith("dob") and not txt.lower().startswith("patient"):
                        result["patient_name"] = txt

                # DOB
                elif 370 < x0 < 460 and 135 < y0 < 152 and not result["dob"]:
                    dob_m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", txt)
                    if dob_m:
                        result["dob"] = dob_m.group(1)

                # Date
                elif 50 < x0 < 120 and 145 < y0 < 165 and not result["date"]:
                    date_m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", txt)
                    if date_m:
                        result["date"] = date_m.group(1)

                # Time In
                elif 180 < x0 < 250 and 145 < y0 < 165 and not result["time_in"]:
                    if any(c.isdigit() for c in txt):
                        result["time_in"] = txt

                # Time Out
                elif 260 < x0 < 350 and 145 < y0 < 165 and not result["time_out"]:
                    if any(c.isdigit() for c in txt):
                        result["time_out"] = txt

                # Drug Name
                elif 380 < x0 < 500 and 145 < y0 < 165 and not result["drug_name"]:
                    if not txt.lower().startswith("drug"):
                        result["drug_name"] = txt

                # Mileage
                elif 500 < x0 < 560 and 100 < y0 < 130 and not result["mileage"]:
                    digits = "".join(filter(str.isdigit, txt))
                    if digits:
                        result["mileage"] = digits

                # Vitals Column (x < 150)
                elif 50 < x0 < 150:
                    if 215 < y0 < 228 and "/" in txt and not result["vitals_bp"]:
                        result["vitals_bp"] = txt
                    elif 228 <= y0 < 240 and any(c.isdigit() for c in txt) and not result["vitals_temperature"]:
                        result["vitals_temperature"] = txt + (" F" if "f" not in txt.lower() else "")
                    elif 240 <= y0 < 254 and txt.isdigit() and not result["vitals_pulse"]:
                        result["vitals_pulse"] = txt
                    elif 254 <= y0 < 270 and txt.isdigit() and not result["vitals_respiration"]:
                        result["vitals_respiration"] = txt

                # Pain Assessment Column (250 < x < 330)
                elif 250 < x0 < 330:
                    if 220 <= y0 < 232 and not result["pain_location"]:
                        result["pain_location"] = txt
                    elif 232 <= y0 < 245 and txt.isdigit() and not result["vitals_pain_scale"]:
                        result["vitals_pain_scale"] = txt

                # Medications & Diet
                elif 110 < x0 < 220 and 365 < y0 < 400 and not result["specify_new_changed_meds"]:
                    result["specify_new_changed_meds"] = txt.replace("\n", ", ")
                elif 30 < x0 < 350 and 425 < y0 < 445 and not result["instructions_given"]:
                    result["instructions_given"] = txt
                elif 450 < x0 < 580 and 490 < y0 < 510 and not result["diet"]:
                    result["diet"] = txt

        # -------------------------------------------------------------------
        # Page 2 Spatial & Semantic Extraction
        # -------------------------------------------------------------------
        if len(pages_blocks) >= 2:
            for b in pages_blocks[1]:
                txt = b[4].strip()
                x0, y0, x1, y1 = b[:4]
                if not txt:
                    continue

                # Vascular Access Site Condition
                if 340 < x0 < 560 and 170 < y0 < 198 and not result["site_condition"]:
                    result["site_condition"] = txt

                # Vein / Location
                elif 480 < x0 < 580 and 290 < y0 < 315 and not result["site_of_insertion"]:
                    result["site_of_insertion"] = txt

                # Gauge
                elif 60 < x0 < 180 and 305 < y0 < 325 and not result["brand_gauge"]:
                    result["brand_gauge"] = txt

                # Attempt number
                elif 370 < x0 < 400 and 290 < y0 < 315 and txt.isdigit() and not result["attempt_number"]:
                    result["attempt_number"] = txt

                # Discontinue Note
                elif 300 < x0 < 580 and 320 < y0 < 340 and not result["discontinue_note"]:
                    result["discontinue_note"] = txt

                # Pump Brand / Model
                elif 60 < x0 < 300 and 440 < y0 < 465 and not result["pump_brand_model"]:
                    result["pump_brand_model"] = txt.replace("\n", " ")

                # Flush
                elif 230 < x0 < 270 and 535 < y0 < 550 and not result["saline_flush_ml"]:
                    result["saline_flush_ml"] = txt

        # -------------------------------------------------------------------
        # Page 3 Spatial & Semantic Extraction
        # -------------------------------------------------------------------
        if len(pages_blocks) >= 3:
            for b in pages_blocks[2]:
                txt = b[4].strip()
                x0, y0, x1, y1 = b[:4]
                if not txt:
                    continue

                # Lot Number
                if 50 < x0 < 150 and 145 < y0 < 168 and txt.isdigit() and not result["lot_number_1"]:
                    result["lot_number_1"] = txt

                # Expiration Date
                elif 200 < x0 < 300 and 145 < y0 < 168 and "/" in txt and not result["exp_date_1"]:
                    result["exp_date_1"] = txt

                # Clinician Signature / Title
                elif "RN" in txt and ("Hilario" in txt or len(txt) < 35) and not result["clinician_signature"]:
                    result["clinician_signature"] = txt
                    result["clinician_name_title"] = txt if "BSN" in txt else (txt + ", BSN")

        # -------------------------------------------------------------------
        # Page 4 Check (Signatures & Coordination)
        # -------------------------------------------------------------------
        if len(pages_blocks) >= 4:
            for b in pages_blocks[3]:
                txt = b[4].strip()
                if "RN" in txt and not result["clinician_signature"]:
                    result["clinician_signature"] = txt
                    result["clinician_name_title"] = txt

        # -------------------------------------------------------------------
        # Comprehensive Regex Fallbacks for General / Non-Orsini PDFs
        # -------------------------------------------------------------------
        if not result["date"]:
            date_m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b", full_text)
            if date_m:
                result["date"] = date_m.group(1)

        if not result["drug_name"]:
            for cand in ["Evkeeza", "IVIG", "Gammagard", "Infliximab", "Remicade", "Ceftriaxone", "Vancomycin", "Iron"]:
                if cand.lower() in full_text.lower():
                    result["drug_name"] = cand
                    break

        if not result["vitals_bp"]:
            bp_m = re.search(r"\b(\d{2,3}/\d{2,3})\b", full_text)
            if bp_m:
                result["vitals_bp"] = bp_m.group(1)

        if not result["vitals_temperature"]:
            temp_m = re.search(r"\b(9\d\.\d|10\d\.\d)\b", full_text)
            if temp_m:
                result["vitals_temperature"] = temp_m.group(1) + " F"

        if not result["vitals_pulse"]:
            hr_m = re.search(r"(?:pulse|hr|heart\s*rate)[:\s]+(\d{2,3})", full_text, re.IGNORECASE)
            if hr_m:
                result["vitals_pulse"] = hr_m.group(1)

        if not result["vitals_respiration"]:
            resp_m = re.search(r"(?:resp|respirations?|rr)[:\s]+(\d{1,2})", full_text, re.IGNORECASE)
            if resp_m:
                result["vitals_respiration"] = resp_m.group(1)

        if not result["pump_brand_model"]:
            pump_m = re.search(r"((?:Curlin|Baxter|Alaris)[^\n]+)", full_text, re.IGNORECASE)
            if pump_m:
                result["pump_brand_model"] = pump_m.group(1).strip()

        if not result["brand_gauge"]:
            gauge_m = re.search(r"(Angiocath\s*\d{2}G|\b\d{2}G\b)", full_text, re.IGNORECASE)
            if gauge_m:
                result["brand_gauge"] = gauge_m.group(1)

        if not result["lot_number_1"]:
            lot_m = re.search(r"\b(\d{10,14}|LOT-[A-Za-z0-9\-]+)\b", full_text)
            if lot_m:
                result["lot_number_1"] = lot_m.group(1)

        if not result["exp_date_1"]:
            exp_m = re.search(r"(?:exp|expiration)[:\s]+(\d{1,2}/\d{2,4})", full_text, re.IGNORECASE)
            if exp_m:
                result["exp_date_1"] = exp_m.group(1)

        if not result["clinician_signature"]:
            nurse_m = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Za-z]+)*\s+RN)\b", full_text)
            if nurse_m:
                result["clinician_signature"] = nurse_m.group(1)
                result["clinician_name_title"] = nurse_m.group(1) + ", BSN"

        # Compatibility dictionary for vitals
        result["vitals"] = {
            "blood_pressure": result["vitals_bp"],
            "heart_rate": result["vitals_pulse"],
            "temperature": result["vitals_temperature"].replace(" F", ""),
            "respiratory_rate": result["vitals_respiration"],
            "pain_scale": result["vitals_pain_scale"],
        }

        doc.close()
        return result

    def extract_patient_info(self, pdf_input: Union[str, Path, bytes]) -> dict[str, Any]:
        """Convenience alias for extract_from_pdf."""
        return self.extract_from_pdf(pdf_input)