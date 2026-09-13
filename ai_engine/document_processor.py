"""
Clinical Document Digitization & OCR Processor for Orsini Infusion Nursing Forms
Converts scanned/photographed physical nursing forms into structured Orsini JSON schemas.
Supports Google Gemini Vision (Gemini 3.6 Flash).
"""

from __future__ import annotations

import os
import json
import base64
import logging
from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    _HAS_GEMINI = True
except ImportError:
    _HAS_GEMINI = False

from .medical_nlp import (
    MedicalNLP,
    ORSINI_SCHEMA,
    PAGE1_SCHEMA,
    PAGE2_SCHEMA,
    PAGE3_SCHEMA,
    PAGE4_SCHEMA,
)

logger = logging.getLogger(__name__)
load_dotenv()

_nlp = MedicalNLP()

# Standard image extensions supported across vision pipelines
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

EXTRACTION_PROMPT = """You are a clinical document digitization assistant for the Orsini Infusion Nursing Notes: Adult form.

The form has 4 pages:
- Page 1: Patient info, pre-infusion vitals, medications, respiratory, pain assessment, cardiopulmonary, neurological, musculoskeletal, skin, GI
- Page 2: IV access, pump, medications administered, labs
- Page 3: Lot numbers, solution/medication infusion table, vitals flow sheet, narrative
- Page 4: Care coordination, progress goals, teaching, clinician/patient signatures, discharge planning

Your tasks:
1. Perform OCR on the image — read every field, checkbox, and handwritten entry.
2. Map all extracted data into the provided JSON schema.
3. For checkboxes: set true if checked/marked, false if empty.
4. For infusion_table and vitals_flow_sheet: output as JSON arrays of objects.
5. Fill only fields with clear evidence; leave others as "" or false.
6. Output ONLY valid JSON — no extra text.
"""


def _sanitize_json_response(raw_text: str) -> dict[str, Any]:
    """
    Strips markdown code fences (```json ... ```) from vision model responses.

    Args:
        raw_text: Raw output string from vision model.

    Returns:
        Cleaned and parsed dictionary.
    """
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    return json.loads(cleaned)


class DocumentProcessor:
    """
    Processes uploaded or scanned Orsini Infusion Nursing Notes forms:
    - High-fidelity optical character recognition (OCR) via Gemini 3.6 Flash Vision.
    - Automated checkbox and tabular flow-sheet extraction.
    - HIPAA Safe Harbor scrub of verbatim OCR text.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initializes the document processor.

        Args:
            provider: Inference provider ('gemini' or 'mock').
            model: Optional model identifier override.
            api_key: Optional API key override.
        """
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if provider:
            self.provider = provider.lower()
            self.api_key = api_key or (gemini_key if self.provider == "gemini" else None)
        elif api_key:
            self.provider = "gemini"
            self.api_key = api_key
        elif gemini_key:
            self.provider = "gemini"
            self.api_key = gemini_key
        else:
            self.provider = "mock"
            self.api_key = None

        if self.provider == "gemini":
            self.model = model or "models/gemini-3.6-flash"
            if _HAS_GEMINI and self.api_key:
                genai.configure(api_key=self.api_key)
            self.client = None
        else:
            self.provider = "mock"
            self.model = "mock-engine"
            self.client = None

    def process_image(self, image_path: str, page: Optional[int] = None) -> dict[str, Any]:
        """
        Extracts structured clinical data and checkboxes from a single Orsini page image.

        Args:
            image_path: Path to the image file on disk.
            page: Specific form page number (1-4). If None, full schema is targeted.

        Returns:
            Dictionary matching the Orsini schema plus '_raw_text' OCR transcription.
        """
        file_path = Path(image_path)
        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported types: {SUPPORTED_EXTENSIONS}")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please configure GEMINI_API_KEY in your .env file.")

        if not file_path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        page_schemas = {1: PAGE1_SCHEMA, 2: PAGE2_SCHEMA, 3: PAGE3_SCHEMA, 4: PAGE4_SCHEMA}
        schema = page_schemas.get(page, ORSINI_SCHEMA)

        if self.provider == "gemini":
            from PIL import Image
            img = Image.open(str(file_path))
            genai.configure(api_key=self.api_key)
            model_inst = genai.GenerativeModel(
                model_name=self.model,
                system_instruction=EXTRACTION_PROMPT,
                generation_config={"response_mime_type": "application/json", "temperature": 0.1},
            )
            prompt = (
                f"{'Page ' + str(page) + ' schema' if page else 'Full form schema'}:\n"
                f"{json.dumps(schema, indent=2)}\n\n"
                "Also include a '_raw_text' key with all extracted text verbatim."
            )
            response = model_inst.generate_content([img, prompt])
            result = _sanitize_json_response(response.text)
        else:
            result = dict(schema)
            result["patient_name"] = ""
            result["_raw_text"] = "Scanned Orsini form processed in simulation mode."

        # Scrub PHI from raw extracted OCR text to ensure HIPAA compliance
        if "_raw_text" in result and isinstance(result["_raw_text"], str):
            result["_raw_text"] = _nlp.scrub_phi(result["_raw_text"])

        # Guarantee all schema keys exist in output
        for key, default in schema.items():
            result.setdefault(key, default)

        return result

    def process_form(self, image_paths: list[str]) -> dict[str, Any]:
        """
        Sequentially processes multi-page scanned forms (up to 4 pages) and merges them
        into a unified clinical record.

        Args:
            image_paths: Ordered list of image paths [page1, page2, page3, page4].

        Returns:
            Single merged dictionary covering all populated Orsini form fields.
        """
        merged = dict(ORSINI_SCHEMA)
        raw_texts = []

        for index, path in enumerate(image_paths, start=1):
            page_num = index if index <= 4 else None
            page_result = self.process_image(path, page=page_num)

            if "_raw_text" in page_result:
                raw_texts.append(page_result.pop("_raw_text"))

            # Merge populated fields
            for key, value in page_result.items():
                if value not in ("", False, [], None):
                    merged[key] = value

        if raw_texts:
            merged["_raw_text"] = "\n---\n".join(raw_texts)

        return merged
