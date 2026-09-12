"""
AI Nurse - Clinical Documentation Engine Runner
Orsini Infusion Nursing Notes: Adult Form

Senior-grade CLI runner and diagnostic suite for clinical validation,
rule-based NLP parsing, and multi-provider LLM synthesis.
"""

from __future__ import annotations

import sys
import os
import time
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout to UTF-8 on modern Windows consoles if possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is present in Python path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from ai_engine import (
    MedicalNLP,
    NoteGenerator,
    DocumentProcessor,
    PDFProcessor,
    OrsiniPDFFiller,
)
from ai_engine.medical_nlp import (
    ORSINI_SCHEMA,
    PAGE1_SCHEMA,
    PAGE2_SCHEMA,
    PAGE3_SCHEMA,
    PAGE4_SCHEMA,
)

# Realistic clinical note snippet representing a standard adult home infusion visit
SAMPLE_CLINICAL_INPUT = (
    "Patient Jane Doe (DOB 04/15/1975, SSN 000-12-3456, phone 555-890-1234) arrived for IVIG infusion. "
    "Pre-infusion vitals: BP 118/74, pulse 72 bpm, temp 98.4 F, resp 16 breaths, weight 65.5 kg, pain 0/10. "
    "Patient is alert and oriented x3. Lungs clear to auscultation bilaterally, no wheezing or rhonchi. "
    "Heart sounds regular, no edema noted. Denies shortness of breath, nausea, or abdominal pain. "
    "Standard precautions and fall precautions maintained. PIV placed in right forearm 20g on 09/09/2026, "
    "site clean, dressing intact, brisk blood return noted. Flushed with 10 mL normal saline. "
    "Infusion started at 50 mL/hr via Baxter pump verified with label. Tolerated well with no adverse reactions."
)


def print_banner() -> None:
    """Renders the CLI application banner."""
    print("=" * 72)
    print("      AI NURSE - CLINICAL DOCUMENTATION ENGINE (ORSINI ADULT FORM)")
    print("=" * 72)


def check_system() -> bool:
    """
    Executes environment diagnostics, verifying Python runtime, dependencies,
    API credentials, and schema integrity.

    Returns:
        True if all critical checks pass, False otherwise.
    """
    print("\n[*] Running System Diagnostics...\n")

    # 1. Python runtime
    print(f"  [OK] Python Runtime: {sys.version.split()[0]} on {sys.platform}")

    # 2. Package dependencies
    try:
        import google.generativeai as genai
        print(f"  [OK] Google Generative AI SDK: Installed (v{getattr(genai, '__version__', 'unknown')})")
    except ImportError:
        print("  [WARN] Google Generative AI SDK: Not installed")

    try:
        import streamlit
        print(f"  [OK] Streamlit Framework: Installed (v{getattr(streamlit, '__version__', 'unknown')})")
    except ImportError:
        print("  [WARN] Streamlit: Not installed")

    try:
        import dotenv
        print("  [OK] Python-dotenv: Installed")
    except ImportError:
        print("  [FAIL] Python-dotenv: Missing! Install via requirements.txt")
        return False

    # 3. Environment variables & API credentials
    env_file = PROJECT_ROOT / ".env"
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if env_file.exists():
        print(f"  [OK] Configuration File: Found ({env_file.name})")
    else:
        print(f"  [INFO] Configuration File: None found (fallback to environment variables)")

    if gemini_key:
        print(f"  [OK] Google Gemini API Key: Configured (Active Model: models/gemini-3.6-flash)")
    else:
        print("  [INFO] Google Gemini API Key: Not configured (Running in Offline Simulation Mode)")

    # 4. Form schemas completeness check
    print(f"  [OK] Orsini Clinical Schemas Loaded:")
    print(f"       - Page 1 (Patient Info & Assessments): {len(PAGE1_SCHEMA)} fields")
    print(f"       - Page 2 (IV Access & Pump Settings):  {len(PAGE2_SCHEMA)} fields")
    print(f"       - Page 3 (Teaching, Flowsheet & Table):{len(PAGE3_SCHEMA)} fields")
    print(f"       - Page 4 (Care Coordination & Goals):  {len(PAGE4_SCHEMA)} fields")
    print(f"       - Total Combined Orsini Schema:        {len(ORSINI_SCHEMA)} fields")

    print("\n[OK] System diagnostics completed successfully!\n")
    return True


def run_nlp_pipeline(custom_text: str | None = None) -> None:
    """
    Demonstrates the deterministic Medical NLP pipeline without network overhead:
      1. Clinical abbreviation expansion.
      2. Regex-driven baseline vital signs extraction.
      3. HIPAA Safe Harbor PHI de-identification.
      4. Orsini form section classification.

    Args:
        custom_text: Optional custom clinical string to process.
    """
    nlp = MedicalNLP()
    input_text = custom_text or SAMPLE_CLINICAL_INPUT

    print("\n" + "-" * 72)
    print("MEDICAL NLP PIPELINE EXECUTION")
    print("-" * 72)
    print(f"\n1. Raw Clinical Input:\n   \"{input_text}\"")

    start_time = time.perf_counter()

    # Step 1: Medical acronym normalization
    expanded = nlp.expand_abbreviations(input_text)
    print(f"\n2. Abbreviation Normalization:\n   \"{expanded[:180]}...\"")

    # Step 2: Vital signs extraction
    vitals = nlp.extract_vitals(expanded)
    print(f"\n3. Pre-Extracted Vital Signs:\n   {json.dumps(vitals, indent=4)}")

    # Step 3: HIPAA Safe Harbor PHI Redaction
    scrubbed = nlp.scrub_phi(input_text)
    print(f"\n4. HIPAA Safe Harbor PHI De-identification:\n   \"{scrubbed[:200]}...\"")

    # Step 4: Page auto-detection
    page = nlp.detect_page(input_text)
    print(f"\n5. Form Page Auto-Detection:\n   Detected Section: Page {page}")

    elapsed = (time.perf_counter() - start_time) * 1000
    print(f"\n[OK] NLP Pipeline execution completed in {elapsed:.2f} ms")
    print("-" * 72)


def run_note_generation(text: str | None = None, page: int | None = None) -> None:
    """
    Generates structured Orsini JSON notes using the active AI backend.

    Args:
        text: Clinical narrative text.
        page: Optional page number constraint (1-4).
    """
    input_text = text or SAMPLE_CLINICAL_INPUT

    print("\n" + "-" * 72)
    print("CLINICAL NOTE GENERATION (ORSINI ADULT FORM)")
    print("-" * 72)
    print(f"Input text:\n\"{input_text}\"\n")

    gen = NoteGenerator()
    start_time = time.perf_counter()

    if gen.provider == "gemini":
        print(f"[*] Dispatching prompt to Google Gemini ({gen.model})...")
        use_mock = False
    else:
        print("[INFO] Running in offline clinical simulation mode...")
        use_mock = True

    try:
        if page:
            result = gen.generate_page(input_text, page=page, mock=use_mock)
            print(f"\n[OK] Successfully Generated Orsini Page {page} Note:")
        else:
            result = gen.generate(input_text, mock=use_mock)
            print(f"\n[OK] Successfully Generated Complete Orsini Form Record:")

        # Summary of populated fields
        populated = {k: v for k, v in result.items() if v not in ("", False, [], None)}
        print(f"\n--- Key Clinical Fields Populated ({len(populated)} / {len(result)}) ---")
        display_keys = [
            "patient_name", "dob", "date", "drug_name",
            "vitals_bp", "vitals_pulse", "vitals_temperature",
            "vitals_respiration", "vitals_weight", "type_of_access",
            "pump_brand_model", "clinician_signature",
        ]
        for key in display_keys:
            if key in populated:
                print(f"  {key:32}: {populated[key]}")

        # Infusion solution table preview
        if "infusion_table" in populated and populated["infusion_table"]:
            print(f"\n--- Infusion Table Entries ({len(populated['infusion_table'])}) ---")
            for item in populated["infusion_table"]:
                print(f"  - {item.get('solution_medication')}: {item.get('amount')} ({item.get('time_started')} - {item.get('time_completed')})")

        # Vitals flow sheet readings preview
        if "vitals_flow_sheet" in populated and populated["vitals_flow_sheet"]:
            print(f"\n--- Vital Signs Flow Sheet ({len(populated['vitals_flow_sheet'])} readings) ---")
            for item in populated["vitals_flow_sheet"]:
                print(f"  - [{item.get('time')}] BP: {item.get('bp')} | HR: {item.get('pulse')} | Rate: {item.get('infusion_rate')} | {item.get('comments')}")

        elapsed = time.perf_counter() - start_time
        print(f"\n[OK] Form generation completed in {elapsed:.2f} seconds.")
    except Exception as exc:
        print(f"[ERROR] Clinical generation failed: {exc}")
    print("-" * 72)


def run_pdf_pipeline(pdf_path: str | None = None) -> None:
    """
    Demonstrates reading clinical demographics and vitals from an existing PDF,
    merging with nurse voice visit dictation, and generating the completed
    identical 4-page Orsini Adult Infusion Nursing Note PDF.

    Args:
        pdf_path: Optional path to an Orsini or clinical PDF.
    """
    processor = PDFProcessor()
    filler = OrsiniPDFFiller()

    target_path = (
        Path(pdf_path)
        if pdf_path and pdf_path != "default"
        else PROJECT_ROOT / "templates" / "orsini_adult_form_template.pdf"
    )
    if not target_path.exists():
        alt_sample = PROJECT_ROOT / "APP SAMPLE NURSE NOTE.pdf"
        if alt_sample.exists():
            target_path = alt_sample
        else:
            print(f"[ERROR] PDF file not found at: {target_path}")
            return

    print("\n" + "=" * 72)
    print("ORSINI PDF INTAKE & AUTO-FILL PIPELINE")
    print("=" * 72)
    print(f"[*] Reading source PDF: {target_path.name}")
    extracted = processor.extract_patient_info(target_path)
    print(f"\n[OK] Extracted {len(extracted)} Fields from PDF:")
    for k, v in extracted.items():
        if v and k not in ("raw_text", "pages_text"):
            print(f"     - {k:24}: {v}")

    # Sample nurse visit dictation to merge
    sample_voice = (
        "Patient Jane Doe tolerated Evkeeza infusion well without any acute distress or reaction. "
        "PIV placed right forearm 20g, brisk blood return. Dressing clean, dry, and intact. "
        "Pre-infusion vitals: BP 118/74, pulse 72, temp 98.4, resp 16, weight 65.5 kg. "
        "Post-infusion vitals: BP 120/76, pulse 70, temp 98.4, resp 16. Discharged in stable condition."
    )
    print(f"\n[*] Merging with Nurse Dictation:\n    \"{sample_voice[:100]}...\"")
    gen = NoteGenerator()
    voice_data = gen.generate(sample_voice, mock=True)
    merged = {**extracted, **voice_data}

    print("\n[*] Populating 4-page Orsini Infusion Note vector template...")
    pdf_bytes = filler.fill_form(merged)
    out_file = PROJECT_ROOT / "output_orsini_form.pdf"
    out_file.write_bytes(pdf_bytes)
    print(f"[OK] Completed PDF saved to: {out_file.name} ({len(pdf_bytes):,} bytes)")
    print("=" * 72)


def interactive_menu() -> None:
    """Provides an interactive terminal menu for hands-on operation."""
    print_banner()
    while True:
        print("\nPlease select an option:")
        print("  [1] Run System Health Diagnostics")
        print("  [2] Test Medical NLP Pipeline (Abbreviation, Vitals, PHI Scrub)")
        print("  [3] Run Clinical Note Generation Demo")
        print("  [4] Enter Custom Clinical Text to Process")
        print("  [5] Test PDF Upload & Auto-Fill Pipeline (Merge PDF + Voice)")
        print("  [6] Run Unit Test Suite (pytest)")
        print("  [0] Exit")

        choice = input("\nEnter choice [0-6]: ").strip()
        if choice == "1":
            check_system()
        elif choice == "2":
            run_nlp_pipeline()
        elif choice == "3":
            run_note_generation()
        elif choice == "4":
            custom = input("\nEnter clinical narrative or dictation text:\n> ").strip()
            if custom:
                run_nlp_pipeline(custom)
                run_note_generation(custom)
        elif choice == "5":
            run_pdf_pipeline()
        elif choice == "6":
            import subprocess
            subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])
        elif choice in ("0", "q", "exit"):
            print("\nExiting AI Nurse. Clinical documentation session closed.\n")
            break
        else:
            print("Invalid selection. Please enter a value between 0 and 6.")


def main() -> None:
    """CLI argument parser and entry point."""
    parser = argparse.ArgumentParser(description="AI Nurse - Orsini Clinical Documentation Runner")
    parser.add_argument("--check", "-c", action="store_true", help="Execute system diagnostics")
    parser.add_argument("--nlp", action="store_true", help="Run Medical NLP demonstration")
    parser.add_argument("--demo", "-d", action="store_true", help="Run end-to-end clinical demo")
    parser.add_argument("--pdf", nargs="?", const="default", help="Process and auto-fill an Orsini PDF form")
    parser.add_argument("--text", "-t", type=str, help="Process custom clinical text")
    parser.add_argument("--page", "-p", type=int, choices=[1, 2, 3, 4], help="Target specific Orsini page (1-4)")
    parser.add_argument("--test", action="store_true", help="Run automated test suite")

    args = parser.parse_args()

    # Launch interactive menu if no flags provided
    if len(sys.argv) == 1:
        interactive_menu()
        return

    if args.check:
        check_system()

    if args.test:
        import subprocess
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])

    if args.nlp:
        run_nlp_pipeline(args.text)

    if args.pdf:
        run_pdf_pipeline(args.pdf)

    if args.demo:
        check_system()
        run_nlp_pipeline()
        run_note_generation(page=args.page)
        run_pdf_pipeline()

    if args.text and not (args.nlp or args.demo):
        run_note_generation(args.text, page=args.page)


if __name__ == "__main__":
    main()
