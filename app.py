"""
AI Nurse - Streamlit Clinical Documentation Assistant
Orsini Infusion Nursing Notes: Adult Form (N-01-C17)
Workflow: Upload Blank PDF -> Voice Dictation -> Auto-Fill PDF -> View Filled Data Below -> Download PDF
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
import streamlit as st
from streamlit.runtime import exists

# If executed directly with 'python app.py', automatically delegate to 'streamlit run app.py'
if not exists():
    print("[*] Direct Python execution detected. Automatically launching Streamlit web server...")
    cmd = [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve())] + sys.argv[1:]
    sys.exit(subprocess.call(cmd))

# Ensure project root is present in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from ai_engine import (
    MedicalNLP,
    NoteGenerator,
    PDFProcessor,
    OrsiniPDFFiller,
    merge_clinical_data,
)

st.set_page_config(
    page_title="AI Nurse - Orsini Clinical Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS for clinical styling (hides sidebar completely)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }
    .main-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.2rem;
    }
    .metric-container {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
    }
</style>
""", unsafe_allow_html=True)

DEFAULT_SAMPLE_DICTATION = (
    "Patient Jane smite (DOB 04/05/1988) presented on 09/11/2025 for scheduled IVIG infusion. "
    "Pre-infusion vitals: BP 118/74, pulse 72, temperature 98.4 F, resp 16, weight 65.5 kg, pain 0/10. "
    "20-gauge PIV placed in right forearm, 2nd attempt, patent with brisk blood return. "
    "Infusion started at 09:00 AM, completed at 11:30 AM via Baxter pump. Lot 99281726, exp 05/26. "
    "Flushed with 10 mL NS. Patient tolerated infusion well without adverse event. Nurse Sarah Connor RN."
)

nlp = MedicalNLP()


def main() -> None:
    """Streamlit Application Entry Point."""
    # Detect API Key from environment or Streamlit Cloud Secrets
    gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    if not gemini_key:
        try:
            if "GEMINI_API_KEY" in st.secrets:
                gemini_key = st.secrets["GEMINI_API_KEY"]
                os.environ["GEMINI_API_KEY"] = gemini_key
            elif "GOOGLE_API_KEY" in st.secrets:
                gemini_key = st.secrets["GOOGLE_API_KEY"]
                os.environ["GOOGLE_API_KEY"] = gemini_key
        except Exception:
            pass

    provider_choice = "gemini" if gemini_key else "mock"
    user_api_key = gemini_key or None
    gen = NoteGenerator(provider=provider_choice, api_key=user_api_key)

    pdf_processor = PDFProcessor()
    blank_template_path = PROJECT_ROOT / "templates" / "orsini_blank_template.pdf"
    if not blank_template_path.exists():
        blank_template_path = PROJECT_ROOT / "templates" / "orsini_adult_form_template.pdf"

    filler = OrsiniPDFFiller(template_path=blank_template_path)

    # Header section
    st.markdown('<div class="main-title">🩺 AI Nurse Documentation Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-title">1. Upload a blank PDF template &nbsp;|&nbsp; '
        '2. Dictate visit observations via voice &nbsp;|&nbsp; '
        '3. AI auto-fills & downloads the completed official 4-page Orsini PDF</div>',
        unsafe_allow_html=True,
    )

    # -----------------------------------------------------------------------
    # Step 1: Upload Blank PDF & Step 2: Nurse Spoken Dictation
    # -----------------------------------------------------------------------
    col_p1, col_p2 = st.columns([1, 1], gap="medium")

    with col_p1:
        st.markdown("#### 📄 Step 1: Upload Blank PDF Template")
        st.caption("Upload your blank Orsini clinical PDF (no data filled).")
        uploaded_pdf = st.file_uploader(
            "Choose a blank PDF template:",
            type=["pdf"],
            key="blank_pdf_uploader_widget",
            help="Upload a blank Orsini Nursing Form PDF template to be filled.",
        )

        st.caption("Or load the standard blank template with 1 click:")
        if st.button("📄 Load Official Blank Orsini Template", key="load_blank_template_btn", use_container_width=True):
            if blank_template_path.exists():
                st.session_state["active_pdf_path"] = str(blank_template_path)
                st.session_state["active_pdf_name"] = "orsini_blank_template.pdf (Official Blank Form)"
                st.session_state.pop("filled_pdf_bytes", None)
                st.session_state.pop("filled_pdf_previews", None)
                with open(blank_template_path, "rb") as f:
                    st.session_state["uploaded_pdf_previews"] = filler.render_preview_images(f.read())
                st.rerun()

        if uploaded_pdf is not None:
            pdf_save_path = PROJECT_ROOT / f"uploaded_{uploaded_pdf.name}"
            file_bytes = uploaded_pdf.getvalue()
            with open(pdf_save_path, "wb") as f:
                f.write(file_bytes)

            if st.session_state.get("active_pdf_path") != str(pdf_save_path):
                st.session_state["active_pdf_path"] = str(pdf_save_path)
                st.session_state["active_pdf_name"] = uploaded_pdf.name
                st.session_state.pop("filled_pdf_bytes", None)
                st.session_state.pop("filled_pdf_previews", None)
                st.session_state["uploaded_pdf_previews"] = filler.render_preview_images(file_bytes)
                st.rerun()

        active_pdf = st.session_state.get("active_pdf_path")
        if active_pdf and os.path.exists(active_pdf):
            st.success(f"**Loaded PDF:** {st.session_state.get('active_pdf_name')}")
            if "uploaded_pdf_previews" not in st.session_state:
                with open(active_pdf, "rb") as f:
                    st.session_state["uploaded_pdf_previews"] = filler.render_preview_images(f.read())

    with col_p2:
        st.markdown("#### 🎙️ Step 2: Nurse Voice Dictation")
        st.caption("Speak all patient, vitals, medication, and IV details via microphone.")
        mic_audio = st.audio_input(
            "Record voice dictation via microphone:",
            key="live_mic_widget",
            help="Click microphone icon to record your clinical visit observations.",
        )

        if mic_audio is not None:
            mic_file_path = PROJECT_ROOT / "recorded_nurse_mic.wav"
            with open(mic_file_path, "wb") as f:
                f.write(mic_audio.getbuffer())
            st.session_state["active_audio"] = str(mic_file_path)
            st.session_state["audio_source_name"] = "Live Microphone Recording (mic.wav)"

        st.caption("Or test with pre-recorded sample voice dictation:")
        if st.button("🎧 Load Sample Nurse Voice (Jane smite / IVIG)", key="sample_voice_btn", use_container_width=True):
            sample_path = PROJECT_ROOT / "sample_nurse_voice.wav"
            if sample_path.exists():
                st.session_state["active_audio"] = str(sample_path)
                st.session_state["audio_source_name"] = "sample_nurse_voice.wav"

        active_audio_path = st.session_state.get("active_audio")
        if active_audio_path and os.path.exists(active_audio_path):
            st.success(f"**Loaded Audio:** {st.session_state.get('audio_source_name')}")
            st.audio(active_audio_path)

    st.markdown("<br>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Step 3: Process Voice & Auto-Fill Blank PDF
    # -----------------------------------------------------------------------
    process_btn = st.button(
        "✨ Process Voice Dictation & Auto-Fill Blank PDF",
        type="primary",
        use_container_width=True,
        key="process_autofill_btn",
    )

    if process_btn:
        active_pdf = st.session_state.get("active_pdf_path")
        if not active_pdf or not os.path.exists(active_pdf):
            st.warning("⚠️ Please upload a blank PDF template in Step 1 first before auto-filling!")
        else:
            with st.spinner("Processing voice dictation and populating Orsini PDF..."):
                active_audio_path = st.session_state.get("active_audio")
                active_dictation = ""
                if active_audio_path and os.path.exists(active_audio_path):
                    voice_res = gen.generate_from_voice(active_audio_path)
                    active_dictation = voice_res.get("_transcript", "")

                if not active_dictation:
                    active_dictation = DEFAULT_SAMPLE_DICTATION

                # Generate structured note
                is_mock = (provider_choice == "mock")
                note_result = gen.generate(active_dictation, mock=is_mock)
                st.session_state["note_result"] = note_result

                # Fill into the uploaded PDF template
                custom_filler = OrsiniPDFFiller(template_path=active_pdf)
                pdf_bytes = custom_filler.fill_form(note_result)
                st.session_state["filled_pdf_bytes"] = pdf_bytes
                st.session_state["filled_pdf_previews"] = custom_filler.render_preview_images(pdf_bytes)
                st.rerun()

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Bottom Display:
    # 1. If not uploaded: nothing shown.
    # 2. If uploaded but not filled yet: show uploaded PDF preview (blank PDF).
    # 3. If filled: show download button & completed filled PDF preview.
    # -----------------------------------------------------------------------
    if st.session_state.get("filled_pdf_bytes"):
        current_note = st.session_state.get("note_result", {})
        st.markdown("### 📥 Download Completed Orsini Nursing Notes (Official PDF)")
        col_dl_btn, col_dl_info = st.columns([2, 5])
        with col_dl_btn:
            p_slug = str(current_note.get("patient_name") or "orsini_note").lower().replace(" ", "_")
            st.download_button(
                label="📄 Download Completed Orsini Form (PDF)",
                data=st.session_state["filled_pdf_bytes"],
                file_name=f"orsini_infusion_note_{p_slug}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="main_pdf_download_btn",
            )
        with col_dl_info:
            st.success("✅ Form filled and compiled in the **exact same 4-page Orsini Adult Infusion Nursing Notes format**.")

        # Interactive visual preview of all 4 filled PDF pages
        st.markdown("#### 👁️ Completed Orsini PDF (Filled with Voice Observations)")
        previews = st.session_state.get("filled_pdf_previews", [])
        page_labels = [
            "📄 Page 1: Patient & Vitals",
            "💉 Page 2: Access & Pump",
            "💧 Page 3: Flow Sheet & Lots",
            "✍️ Page 4: Care & Signatures",
        ]
        p_tabs = st.tabs([page_labels[i] if i < len(page_labels) else f"📄 Page {i+1}" for i in range(len(previews))])
        for p_idx, p_tab in enumerate(p_tabs):
            with p_tab:
                if p_idx < len(previews):
                    st.image(previews[p_idx], use_container_width=True, caption=f"Orsini Adult Infusion Nursing Notes (Form N-01-C17) - Page {p_idx+1}")

    elif st.session_state.get("active_pdf_path") and st.session_state.get("uploaded_pdf_previews"):
        st.markdown("#### 👁️ Uploaded PDF Preview")
        st.caption(
            f"Displaying uploaded template: **{st.session_state.get('active_pdf_name')}**. "
            "Provide voice dictation in Step 2 above and click 'Process Voice Dictation & Auto-Fill Blank PDF' to fill it."
        )
        previews = st.session_state.get("uploaded_pdf_previews", [])
        p_tabs = st.tabs([f"📄 Page {i+1}" for i in range(len(previews))])
        for p_idx, p_tab in enumerate(p_tabs):
            with p_tab:
                if p_idx < len(previews):
                    st.image(previews[p_idx], use_container_width=True, caption=f"{st.session_state.get('active_pdf_name')} - Page {p_idx+1}")


if __name__ == "__main__":
    main()
