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
# Custom CSS for Premium Modern Dark Clinical Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Completely hide sidebar and collapse toggle */
    [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
        display: none !important;
    }

    /* Page container limits and padding */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1240px !important;
    }

    /* Radiant Title */
    .main-title {
        font-size: 2.3rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #60A5FA 0%, #A78BFA 50%, #38BDF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.35rem !important;
        letter-spacing: -0.025em;
    }

    .sub-title {
        font-size: 1.02rem !important;
        color: #94A3B8 !important;
        margin-bottom: 1.8rem !important;
        line-height: 1.6;
    }

    /* Sleek Dark Frosted Cards for Step 1 & Step 2 */
    div[data-testid="column"] > div {
        background: rgba(21, 29, 47, 0.75);
        border: 1px solid rgba(59, 130, 246, 0.22);
        border-radius: 14px;
        padding: 1.6rem 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(14px);
        transition: all 0.25s ease;
    }

    div[data-testid="column"] > div:hover {
        border-color: rgba(99, 102, 241, 0.45);
        box-shadow: 0 12px 35px -8px rgba(37, 99, 235, 0.3);
    }

    /* Headers inside Step Cards */
    h4 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
        font-size: 1.18rem !important;
        letter-spacing: -0.01em;
        margin-bottom: 0.4rem !important;
    }

    /* Captions */
    .stCaption, [data-testid="stCaptionContainer"] {
        color: #64748B !important;
        font-size: 0.88rem !important;
    }

    /* Primary Action Button: Glowing Blue-Indigo Gradient */
    button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.6rem !important;
        font-weight: 600 !important;
        font-size: 1.05rem !important;
        box-shadow: 0 4px 22px rgba(99, 102, 241, 0.45) !important;
        transition: all 0.25s ease !important;
    }

    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8 0%, #6D28D9 100%) !important;
        box-shadow: 0 6px 30px rgba(99, 102, 241, 0.65) !important;
        transform: translateY(-2px);
    }

    /* Secondary Buttons: Dark Slate with subtle border */
    button[kind="secondary"] {
        background: rgba(30, 41, 59, 0.85) !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155 !important;
        border-radius: 9px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover {
        background: rgba(51, 65, 85, 0.95) !important;
        border-color: #60A5FA !important;
        color: #FFFFFF !important;
    }

    /* File Uploader Box */
    [data-testid="stFileUploader"] {
        background: rgba(15, 23, 42, 0.55);
        border: 1px dashed rgba(99, 102, 241, 0.35);
        border-radius: 10px;
        padding: 0.5rem;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid #1E293B;
        padding-bottom: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 10px 18px;
        border-radius: 8px 8px 0 0;
        color: #94A3B8;
        font-weight: 500;
        background-color: transparent;
        border: none;
        transition: all 0.2s ease;
    }

    .stTabs [aria-selected="true"] {
        color: #60A5FA !important;
        background-color: rgba(37, 99, 235, 0.15) !important;
        border-bottom: 2px solid #60A5FA !important;
        font-weight: 600;
    }

    /* Alerts and Badges */
    .stAlert {
        border-radius: 10px;
        background-color: rgba(15, 23, 42, 0.85) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

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
        active_audio_path = st.session_state.get("active_audio")

        if not active_pdf or not os.path.exists(active_pdf):
            st.warning("⚠️ Please upload a blank PDF template in Step 1 first before auto-filling!")
        elif not active_audio_path or not os.path.exists(active_audio_path):
            st.warning("⚠️ Please record your voice dictation in Step 2 before auto-filling!")
        else:
            with st.spinner("Processing voice dictation and populating Orsini PDF..."):
                voice_res = gen.generate_from_voice(active_audio_path)
                active_dictation = voice_res.get("_transcript", "").strip()

                if not active_dictation or active_dictation.startswith("Voice transcription error") or active_dictation.startswith("Voice transcription unavailable"):
                    st.error(f"⚠️ Could not transcribe voice: {active_dictation or 'Empty audio recording'}")
                else:
                    # Generate structured note strictly from actual spoken input
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
