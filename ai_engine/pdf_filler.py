"""
Orsini Infusion Nursing Notes: Adult Form PDF Filler Engine.
Overlays structured clinical documentation onto official 4-page Orsini vector templates,
preserving the exact visual formatting, logos, section borders, tables, and typography.
"""

from __future__ import annotations

import io
import os
import logging
from pathlib import Path
from typing import Any, Optional, Union
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE_PATH = PROJECT_ROOT / "templates" / "orsini_blank_template.pdf"
SAMPLE_TEMPLATE_PATH = PROJECT_ROOT / "templates" / "orsini_adult_form_template.pdf"


class OrsiniPDFFiller:
    """
    Renders structured clinical data directly onto the Orsini 4-page Adult Infusion form.
    Calculates exact coordinate bounding boxes for headers, baseline vitals, checkboxes,
    infusion flow sheets, narrative sections, and nurse signatures.
    """

    def __init__(self, template_path: Optional[Union[str, Path]] = None):
        """
        Initializes the PDF filler engine.

        Args:
            template_path: Path to the clean 4-page Orsini vector template.
                           Defaults to 'templates/orsini_blank_template.pdf'.
        """
        if template_path:
            self.template_path = Path(template_path)
        elif DEFAULT_TEMPLATE_PATH.exists():
            self.template_path = DEFAULT_TEMPLATE_PATH
        elif SAMPLE_TEMPLATE_PATH.exists():
            self.template_path = SAMPLE_TEMPLATE_PATH
        else:
            raise FileNotFoundError("Orsini PDF form template not found in templates directory.")

    def fill_form(
        self,
        data: dict[str, Any],
        output_path: Optional[Union[str, Path]] = None,
    ) -> bytes:
        """
        Populates the 4-page Orsini Infusion Nursing Note with clinical data.

        Args:
            data: Populated clinical note dictionary matching ORSINI_SCHEMA.
            output_path: Optional file path to save the completed PDF.

        Returns:
            Byte string of the completed 4-page PDF document.
        """
        doc = fitz.open(self.template_path)

        # Populate Page 1: Patient demographics, baseline vitals & clinical assessment
        if len(doc) >= 1:
            self._fill_page_1(doc[0], data)

        # Populate Page 2: Vascular access, infusion pump & supplies
        if len(doc) >= 2:
            self._fill_page_2(doc[1], data)

        # Populate Page 3: Teaching, lot numbers, infusion table & flow sheet
        if len(doc) >= 3:
            self._fill_page_3(doc[2], data)

        # Populate Page 4: Care coordination, discharge goals & signatures
        if len(doc) >= 4:
            self._fill_page_4(doc[3], data)

        pdf_bytes = doc.tobytes()
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "wb") as f:
                f.write(pdf_bytes)

        doc.close()
        return pdf_bytes

    def render_preview_images(self, pdf_bytes: bytes, dpi: int = 150) -> list[bytes]:
        """
        Renders pages of a filled PDF document into high-resolution PNG image bytes.

        Args:
            pdf_bytes: Raw bytes of the PDF.
            dpi: Render resolution (default: 150 for crisp web display).

        Returns:
            List of PNG image byte strings (one per page).
        """
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        images: list[bytes] = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
        doc.close()
        return images

    # -----------------------------------------------------------------------
    # PAGE 1 RENDERER
    # -----------------------------------------------------------------------
    def _fill_page_1(self, page: fitz.Page, d: dict[str, Any]) -> None:
        """Overlays patient demographics, baseline vitals, and system checklists."""
        font = "helv"
        black = (0, 0, 0)

        # Patient Header
        p_name = str(d.get("patient_name") or "").strip()
        dob = str(d.get("dob") or "").strip()
        date = str(d.get("date") or "").strip()
        time_in = str(d.get("time_in") or "").strip()
        time_out = str(d.get("time_out") or "").strip()
        drug = str(d.get("drug_name") or "").strip()
        parking = str(d.get("parking") or "").strip()
        mileage = str(d.get("mileage") or "").strip()

        if p_name:
            page.insert_text((100, 148), p_name, fontsize=10, fontname=font, color=black)
        if dob:
            page.insert_text((380, 148), dob, fontsize=10, fontname=font, color=black)
        if date:
            page.insert_text((58, 163), date, fontsize=10, fontname=font, color=black)
        if time_in:
            page.insert_text((195, 163), time_in, fontsize=10, fontname=font, color=black)
        if time_out:
            page.insert_text((285, 163), time_out, fontsize=10, fontname=font, color=black)
        if drug:
            page.insert_text((400, 163), drug, fontsize=10, fontname=font, color=black)
        if parking:
            page.insert_text((440, 120), parking, fontsize=9, fontname=font, color=black)
        if mileage:
            page.insert_text((514, 120), mileage, fontsize=9, fontname=font, color=black)

        # Baseline Vitals
        bp = str(d.get("vitals_bp") or "").strip()
        temp = str(d.get("vitals_temperature") or "").strip()
        pulse = str(d.get("vitals_pulse") or "").strip()
        resp = str(d.get("vitals_respiration") or "").strip()
        weight = str(d.get("vitals_weight") or "").strip()
        pain = str(d.get("vitals_pain_scale") or "").strip()
        pulse_ox = str(d.get("pulse_ox") or "").strip()

        if bp:
            page.insert_text((70, 229), bp, fontsize=10, fontname=font, color=black)
        if temp:
            page.insert_text((82, 242), temp, fontsize=10, fontname=font, color=black)
        if pulse:
            page.insert_text((58, 255), pulse, fontsize=10, fontname=font, color=black)
        if resp:
            page.insert_text((90, 268), resp, fontsize=10, fontname=font, color=black)
        if weight:
            page.insert_text((65, 281), weight, fontsize=10, fontname=font, color=black)
        if pulse_ox:
            page.insert_text((70, 294), pulse_ox, fontsize=10, fontname=font, color=black)

        # Pain Assessment
        pain_loc = str(d.get("pain_location") or "").strip()
        if pain_loc:
            page.insert_text((275, 230), pain_loc, fontsize=8, fontname=font, color=black)
        if pain:
            page.insert_text((292, 243), pain, fontsize=8, fontname=font, color=black)

        # Medications & Notes
        if d.get("specify_new_changed_meds"):
            page.insert_text((128, 380), str(d.get("specify_new_changed_meds")), fontsize=8, fontname=font, color=black)
        if d.get("instructions_given"):
            page.insert_text((35, 438), str(d.get("instructions_given")), fontsize=8, fontname=font, color=black)

        # Assessment Notes & Diet
        if d.get("diet"):
            page.insert_text((470, 502), str(d.get("diet")), fontsize=7.5, fontname=font, color=black)

        # Checkboxes (only draw X if field is explicitly True in data)
        if d.get("standard_precautions_maintained"):
            self._draw_cross(page, (32, 307))
        if d.get("lung_sounds"):
            self._draw_cross(page, (79, 550))
        if d.get("heart_sounds"):
            self._draw_cross(page, (279, 353))
            self._draw_cross(page, (317, 353))
        if d.get("chest_pain_denies") or (pain_loc.lower() == "denies"):
            self._draw_cross(page, (230, 420))
        if d.get("alert"):
            self._draw_cross(page, (230, 560))
        if d.get("oriented_to_person"):
            self._draw_cross(page, (260, 560))
        if d.get("oriented_to_place"):
            self._draw_cross(page, (334, 560))
        if d.get("oriented_to_time"):
            self._draw_cross(page, (365, 560))
        if d.get("pupils_equal"):
            self._draw_cross(page, (340, 600))
        if d.get("skin_intact"):
            self._draw_cross(page, (447, 353))
        if d.get("bowel_sounds_active"):
            self._draw_cross(page, (447, 423))
        if d.get("fall_precaution_maintained"):
            self._draw_cross(page, (446, 290))

    # -----------------------------------------------------------------------
    # PAGE 2 RENDERER
    # -----------------------------------------------------------------------
    def _fill_page_2(self, page: fitz.Page, d: dict[str, Any]) -> None:
        """Overlays vascular access, infusion pump settings, and flushes."""
        font = "helv"
        black = (0, 0, 0)

        p_name = str(d.get("patient_name") or "").strip()
        dob = str(d.get("dob") or "").strip()
        date = str(d.get("date") or "").strip()

        if p_name:
            page.insert_text((100, 124), p_name, fontsize=10, fontname=font, color=black)
        if dob:
            page.insert_text((380, 124), dob, fontsize=10, fontname=font, color=black)
        if date:
            page.insert_text((450, 124), date, fontsize=10, fontname=font, color=black)

        # Vascular Access Details
        site_note = str(d.get("site_condition") or "").strip()
        if site_note:
            page.insert_text((360, 186), site_note, fontsize=9, fontname=font, color=black)

        gauge = str(d.get("brand_gauge") or "").strip()
        if gauge:
            page.insert_text((78, 318), gauge, fontsize=9.5, fontname=font, color=black)

        site = str(d.get("site_of_insertion") or "").strip()
        if site:
            page.insert_text((510, 305), site, fontsize=9.5, fontname=font, color=black)

        attempt = str(d.get("attempt_number") or "").strip()
        if attempt:
            page.insert_text((381, 305), attempt, fontsize=9.5, fontname=font, color=black)

        discontinue_note = str(d.get("discontinue_note") or "").strip()
        if discontinue_note:
            page.insert_text((330, 332), discontinue_note, fontsize=7.5, fontname=font, color=black)

        # Infusion Pump
        pump = str(d.get("pump_brand_model") or "").strip()
        if pump:
            page.insert_text((80, 453), pump, fontsize=7.5, fontname=font, color=black)

        # Flushes
        flush_amt = str(d.get("saline_flush_ml") or "").strip()
        if flush_amt:
            flush_num = "".join(filter(str.isdigit, flush_amt)) or flush_amt
            page.insert_text((250, 545), flush_num, fontsize=8, fontname=font, color=black)
            page.insert_text((68, 558), flush_num, fontsize=8, fontname=font, color=black)

        # Page 2 Checkboxes (only if relevant fields are set)
        type_access = str(d.get("type_of_access") or "").lower()
        if "peripheral" in type_access or "piv" in type_access or (gauge and "picc" not in type_access):
            self._draw_cross(page, (80.5, 198.7))  # Peripheral
        if site:
            if "antecubital" in site.lower():
                self._draw_cross(page, (100.0, 251.0))
            else:
                self._draw_cross(page, (189.0, 251.0))

        if site_note:
            self._draw_cross(page, (80.5, 264.6))  # Site condition: Dry
            self._draw_cross(page, (109.7, 277.7))  # Current dressing intact: Yes
            self._draw_cross(page, (319.5, 290.8))  # Cleansed Chlora-prep
            self._draw_cross(page, (429.7, 290.8))  # Transparent dressing
            self._draw_cross(page, (482.6, 290.8))  # Gauze

        if gauge or attempt:
            self._draw_cross(page, (305.4, 304.3))  # Inserted during visit: Yes

        if discontinue_note:
            self._draw_cross(page, (177.3, 330.3))  # Catheter discontinued: Yes
            self._draw_cross(page, (28.6, 356.9))   # Reason: Therapy completed

        if pump:
            self._draw_cross(page, (362.8, 451.6))  # Pump program verified: Yes
            self._draw_cross(page, (180.2, 465.0))  # Pump settings verified: Yes
            self._draw_cross(page, (390.4, 465.0))  # Pump settings changed: No

        if d.get("therapy_admin_by_nurse"):
            self._draw_cross(page, (90.1, 543.0))   # Therapy admin by: Nurse

    # -----------------------------------------------------------------------
    # PAGE 3 RENDERER
    # -----------------------------------------------------------------------
    def _fill_page_3(self, page: fitz.Page, d: dict[str, Any]) -> None:
        """Overlays medication lot numbers, solution table, and vitals flow sheet."""
        font = "helv"
        black = (0, 0, 0)

        p_name = str(d.get("patient_name") or "").strip()
        dob = str(d.get("dob") or "").strip()
        date = str(d.get("date") or "").strip()

        if p_name:
            page.insert_text((100, 108), p_name, fontsize=10, fontname=font, color=black)
        if dob:
            page.insert_text((380, 108), dob, fontsize=10, fontname=font, color=black)
        if date:
            page.insert_text((486, 108), date, fontsize=10, fontname=font, color=black)

        # Lot Numbers
        lot1 = str(d.get("lot_number_1") or "").strip()
        exp1 = str(d.get("exp_date_1") or "").strip()
        if lot1:
            page.insert_text((74, 156), lot1, fontsize=9, fontname=font, color=black)
        if exp1:
            page.insert_text((242, 156), exp1, fontsize=9, fontname=font, color=black)

        # Solution / Medication Infusion Table
        infusion_rows = d.get("infusion_table") or []
        table_y_coords = [235, 258, 281]
        for idx, row in enumerate(infusion_rows[:3]):
            y = table_y_coords[idx]
            if row.get("solution_medication"):
                page.insert_text((40, y), str(row.get("solution_medication", "")), fontsize=8.5, fontname=font, color=black)
            if row.get("amount"):
                page.insert_text((150, y), str(row.get("amount", "")), fontsize=8.5, fontname=font, color=black)
            if row.get("time_started"):
                page.insert_text((242, y), str(row.get("time_started", "")), fontsize=8.5, fontname=font, color=black)
            if row.get("time_completed"):
                page.insert_text((338, y), str(row.get("time_completed", "")), fontsize=8.5, fontname=font, color=black)
            if row.get("amount_infused"):
                page.insert_text((433, y), str(row.get("amount_infused", "")), fontsize=8.5, fontname=font, color=black)

        # Vital Signs Flow Sheet Table (Titration & Toleration)
        flow_rows = d.get("vitals_flow_sheet") or []
        flow_y_start = 333
        row_height = 23.2
        for idx, row in enumerate(flow_rows[:6]):
            y = flow_y_start + (idx * row_height)
            if row.get("time"):
                page.insert_text((34, y), str(row.get("time", "")), fontsize=8, fontname=font, color=black)
            if row.get("pulse"):
                page.insert_text((92, y), str(row.get("pulse", "")), fontsize=8, fontname=font, color=black)
            if row.get("resp_rate"):
                page.insert_text((152, y), str(row.get("resp_rate", "")), fontsize=8, fontname=font, color=black)
            if row.get("temp"):
                page.insert_text((210, y), str(row.get("temp", "")), fontsize=8, fontname=font, color=black)
            if row.get("bp"):
                page.insert_text((267, y), str(row.get("bp", "")), fontsize=8, fontname=font, color=black)
            if row.get("o2_percent"):
                page.insert_text((326, y), str(row.get("o2_percent", "")), fontsize=8, fontname=font, color=black)
            if row.get("infusion_rate"):
                page.insert_text((385, y), str(row.get("infusion_rate", "")), fontsize=8, fontname=font, color=black)
            if row.get("comments"):
                page.insert_text((442, y), str(row.get("comments", "")), fontsize=7.5, fontname=font, color=black)

        # Narrative Note
        narrative = str(d.get("narrative") or "").strip()
        if narrative:
            page.insert_textbox(fitz.Rect(33, 595, 575, 650), narrative, fontsize=7.5, fontname=font, color=black)

        # Clinician Signature & Date
        sig = str(d.get("clinician_signature") or "").strip()
        nurse = str(d.get("clinician_name_title") or sig).strip()
        if nurse:
            page.insert_text((108, 734), nurse, fontsize=8.5, fontname=font, color=black)
        if sig:
            page.insert_text((460, 734), sig, fontsize=8.5, fontname="hebo", color=black)
        if sig and date:
            page.insert_text((541, 734), date, fontsize=8.5, fontname=font, color=black)

    # -----------------------------------------------------------------------
    # PAGE 4 RENDERER
    # -----------------------------------------------------------------------
    def _fill_page_4(self, page: fitz.Page, d: dict[str, Any]) -> None:
        """Overlays progress goals, patient education, coordination, and signatures."""
        font = "helv"
        black = (0, 0, 0)

        p_name = str(d.get("patient_name") or "").strip()
        dob = str(d.get("dob") or "").strip()
        date = str(d.get("date") or "").strip()
        time_in = str(d.get("time_in") or "").strip()
        time_out = str(d.get("time_out") or "").strip()

        if p_name:
            page.insert_text((100, 108), p_name, fontsize=10, fontname=font, color=black)
        if dob:
            page.insert_text((380, 108), dob, fontsize=10, fontname=font, color=black)
        if date:
            page.insert_text((486, 108), date, fontsize=10, fontname=font, color=black)

        # Progress Goals
        goals = str(d.get("progress_goals") or "").strip()
        if goals:
            page.insert_text((84, 170), goals, fontsize=8, fontname=font, color=black)

        # Teaching
        teaching = str(d.get("teaching_tool_used") or "").strip()
        if teaching:
            page.insert_text((143, 220), teaching, fontsize=8, fontname=font, color=black)
        if d.get("instructed"):
            self._draw_cross(page, (136.4, 233.6))  # Instructed
        if d.get("pt_cg_verbalized_understanding"):
            self._draw_cross(page, (193.1, 233.6))  # Verbalized understanding

        # Discharge / Next Visit Plan
        next_visit = str(d.get("plan_for_next_visit") or "").strip()
        if next_visit:
            page.insert_text((84, 510), next_visit, fontsize=8, fontname=font, color=black)

        # Nurse Signature & Sign-out
        sig = str(d.get("clinician_signature") or "").strip()
        if sig:
            page.insert_text((108, 720), sig, fontsize=8.5, fontname="hebo", color=black)
        if sig and time_in:
            page.insert_text((353, 720), time_in, fontsize=8.5, fontname=font, color=black)
        if sig and time_out:
            page.insert_text((454, 720), time_out, fontsize=8.5, fontname=font, color=black)
        if sig and date:
            page.insert_text((541, 720), date, fontsize=8.5, fontname=font, color=black)

    # -----------------------------------------------------------------------
    # DRAWING HELPER
    # -----------------------------------------------------------------------
    def _draw_cross(self, page: fitz.Page, top_left: tuple[float, float], size: float = 4.0) -> None:
        """Draws a clean checkmark cross [X] in a checkbox."""
        x, y = top_left
        p1 = fitz.Point(x, y)
        p2 = fitz.Point(x + size, y + size)
        p3 = fitz.Point(x + size, y)
        p4 = fitz.Point(x, y + size)
        page.draw_line(p1, p2, color=(0, 0, 0), width=0.9)
        page.draw_line(p3, p4, color=(0, 0, 0), width=0.9)
