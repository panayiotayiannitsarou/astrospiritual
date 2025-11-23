import os
import json
import hashlib
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional

import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============ CONSTANTS (unchanged) ============
SIGNS_GR_TO_EN = {
    "Κριός": "Aries", "Ταύρος": "Taurus", "Δίδυμοι": "Gemini",
    "Καρκίνος": "Cancer", "Λέων": "Leo", "Παρθένος": "Virgo",
    "Ζυγός": "Libra", "Σκορπιός": "Scorpio", "Τοξότης": "Sagittarius",
    "Αιγόκερως": "Capricorn", "Υδροχόος": "Aquarius", "Ιχθύες": "Pisces",
}

SIGNS_GR_LIST = list(SIGNS_GR_TO_EN.keys())
SIGNS_WITH_EMPTY = ["---"] + SIGNS_GR_LIST

SIGN_RULERS = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury",
    "Cancer": "Moon", "Leo": "Sun", "Virgo": "Mercury",
    "Libra": "Venus", "Scorpio": "Pluto", "Sagittarius": "Jupiter",
    "Capricorn": "Saturn", "Aquarius": "Uranus", "Pisces": "Neptune",
}

PLANET_EN_TO_GR = {
    "Sun": "Ήλιος", "Moon": "Σελήνη", "Mercury": "Ερμής",
    "Venus": "Αφροδίτη", "Mars": "Άρης", "Jupiter": "Δίας",
    "Saturn": "Κρόνος", "Uranus": "Ουρανός", "Neptune": "Ποσειδώνας",
    "Pluto": "Πλούτωνας", "Chiron": "Χείρωνας",
    "North Node": "Βόρειος Δεσμός", "AC": "AC", "MC": "MC",
}

PLANETS = [
    ("Ήλιος", "Sun"), ("Σελήνη", "Moon"), ("Ερμής", "Mercury"),
    ("Αφροδίτη", "Venus"), ("Άρης", "Mars"), ("Δίας", "Jupiter"),
    ("Κρόνος", "Saturn"), ("Ουρανός", "Uranus"), ("Ποσειδώνας", "Neptune"),
    ("Πλούτωνας", "Pluto"), ("Βόρειος Δεσμός", "North Node"),
    ("Χείρωνας", "Chiron"), ("AC", "AC"), ("MC", "MC"),
]

ASPECT_OPTIONS = [
    ("Καμία", None),
    ("🔴 ☌ Σύνοδος (0°)", "conjunction"),
    ("🔴 ☍ Αντίθεση (180°)", "opposition"),
    ("🔵 △ Τρίγωνο (120°)", "trine"),
    ("🔴 □ Τετράγωνο (90°)", "square"),
    ("🔵 ⚹ Εξάγωνο (60°)", "sextile"),
]


# ============ UTILITIES ============
def get_openai_client() -> Optional[OpenAI]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def compute_payload_hash(payload: dict) -> str:
    """Compute SHA256 hash for caching."""
    json_str = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode()).hexdigest()


def validate_chart_data(payload: dict) -> List[str]:
    """Validate chart completeness and return warnings."""
    warnings = []
    
    # Check houses
    houses = payload.get("houses", [])
    if len(houses) < 12:
        warnings.append(f"⚠️ Μόνο {len(houses)}/12 οίκοι συμπληρωμένοι")
    
    # Check planets placement
    planets_placed = payload.get("planets_in_houses", [])
    total_planets = len([p for p in PLANETS if p[1] not in ("AC", "MC")])
    if len(planets_placed) < total_planets:
        warnings.append(f"⚠️ Μόνο {len(planets_placed)}/{total_planets} πλανήτες τοποθετημένοι")
    
    # Check aspects
    aspects = payload.get("aspects", [])
    if len(aspects) == 0:
        warnings.append("⚠️ Καμία όψη επιλεγμένη")
    
    return warnings


# ============ OPENAI FUNCTIONS (with caching) ============
@st.cache_data(show_spinner=False)
def generate_basic_report_cached(payload_hash: str, payload: dict) -> str:
    """Cached version of basic report generation."""
    return generate_basic_report_with_openai(payload)


def generate_basic_report_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη: basic_info, houses, planets_in_houses και aspects.
Θέλω να γράψεις ΠΑΝΤΑ σε καλή, καθαρή ελληνική γλώσσα.

Να ακολουθείς αυτή τη δομή αναφοράς:
0. Μικρό κουτάκι με βασικά στοιχεία (Ήλιος, Ωροσκόπος, Σελήνη).
1. ΕΝΟΤΗΤΑ 1 – Οι ακμές των οίκων: για κάθε οίκο 1–12 μια σύντομη παράγραφο με θέμα οίκου + χρώμα ζωδίου ακμής.
2. ΕΝΟΤΗΤΑ 2 – Πλανήτες & κυβερνήτες σε οίκους: για κάθε οίκο, αν έχει πλανήτες γράψε ανάλυση. Αν δεν έχει, εξήγησε τον οίκο μέσω του ζωδίου της ακμής και του κυβερνήτη του ζωδίου.
3. ΕΝΟΤΗΤΑ 3 – Όψεις: Για ΚΑΘΕ όψη που υπάρχει στο JSON να γράφεις ξεχωριστά, χωρίς να τις συγχωνεύεις όλες σε μία γενική παράγραφο.

ΓΕΝΙΚΕΣ ΟΔΗΓΙΕΣ ΥΦΟΥΣ:
- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.
- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό. Όχι μοιρολατρικό.
- Μη χρησιμοποιείς τεχνική ορολογία χωρίς εξήγηση.
- Μη μιλάς για καλό/κακό χάρτη. Μίλα για δυνατότητες, προκλήσεις και εξέλιξη."""

    user_prompt = f"""Παρακάτω είναι τα δεδομένα του χάρτη σε JSON.
Να γράψεις την Προσωπική Έκθεση Γενέθλιου Χάρτη ΜΟΝΟ για τις Ενότητες 0–3.

{json.dumps(payload, ensure_ascii=False, indent=2)}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


@st.cache_data(show_spinner=False)
def generate_section4_report_cached(payload_hash: str, payload: dict) -> str:
    return generate_section4_report_with_openai(payload)


def generate_section4_report_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Με βάση το JSON, θέλω να γράψεις ΜΟΝΟ την ΕΝΟΤΗΤΑ 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία.

4. ΕΝΟΤΗΤΑ 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία

4.1 Κύρια Ταλέντα & Δυνατά Σημεία
4.2 Επαγγέλματα & Κατευθύνσεις που ταιριάζουν συμβολικά
4.3 Ταλέντα που ίσως έχει "ξεχάσει" ότι έχει
4.4 Πώς μπορεί να ξαναβρεί τον "χαμένο" του εαυτό
4.5 Τι είναι καλό να προσέχει

ΓΕΝΙΚΕΣ ΟΔΗΓΙΕΣ:
- Γράψε σε απλή, καθαρή ελληνική γλώσσα.
- Να είναι ζεστό, ενδυναμωτικό, θεραπευτικό."""

    user_prompt = f"""Παρακάτω τα δεδομένα του χάρτη.
Γράψε ΜΟΝΟ την Ενότητα 4 με τις υποενότητες 4.1–4.5.

{json.dumps(payload, ensure_ascii=False, indent=2)}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


@st.cache_data(show_spinner=False)
def generate_section5_aspects_cached(payload_hash: str, payload: dict) -> str:
    return generate_section5_aspects_with_openai(payload)


def generate_section5_aspects_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη.

Χρησιμοποίησε τα στοιχεία των οίκων και των πλανητών σε οίκους ΜΟΝΟ ως πλαίσιο.
ΔΕΝ θα γράψεις ανάλυση οίκων ή ενότητα για πλανήτες σε οίκους.
Θα γράψεις ΜΟΝΟ την ΕΝΟΤΗΤΑ 5 – Όψεις, χωρισμένη σε υποενότητες.

5. ΕΝΟΤΗΤΑ 5 – Όψεις (σε υποενότητες)

5Α. Βασικές ψυχολογικές όψεις
- Εδώ θα βάλεις όψεις που περιλαμβάνουν τον Ήλιο (Sun), τη Σελήνη (Moon), τον Ωροσκόπο (AC) ή τον κυβερνήτη Ωροσκόπου.
- Για κάθε τέτοια όψη γράψε ΜΙΑ ξεχωριστή, μικρή παράγραφο 3–4 προτάσεων.

5Β. Θεραπευτικές / καρμικές όψεις
- Εδώ θα βάλεις όψεις που περιλαμβάνουν Χείρωνα (Chiron), Βόρειο Δεσμό (North Node), Κρόνο (Saturn) ή Πλούτωνα (Pluto).
- Για κάθε τέτοια όψη γράψε ΜΙΑ ξεχωριστή παράγραφο 3–5 προτάσεων.

5Γ. Λοιπές όψεις
- Εδώ θα βάλεις όλες τις υπόλοιπες όψεις που απομένουν.
- Για κάθε μία γράψε ΜΙΑ ξεχωριστή μικρή παράγραφο 2–4 προτάσεων.

ΣΗΜΑΝΤΙΚΟ:
- Η λίστα 'aspects' στο JSON περιέχει ΜΟΝΟ τις όψεις που θέλω να αναλύσεις.
- Γράψε ξεχωριστή παράγραφο για ΚΑΘΕ όψη που υπάρχει στο JSON, χωρίς να τις συγχωνεύσεις.

ΥΦΟΣ:
- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.
- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό, χωρίς μοιρολατρία.
- Μην προσθέτεις γενική εισαγωγή για τις όψεις· ξεκίνα κατευθείαν από την υποενότητα 5Α."""

    user_prompt = f"""Παρακάτω είναι τα δεδομένα του χάρτη σε JSON.

Χρησιμοποίησέ τα ως πλήρες πλαίσιο (basic_info, houses, planets_in_houses),
αλλά γράψε ΜΟΝΟ την Ενότητα 5 – Όψεις, με τις υποενότητες 5Α, 5Β, 5Γ, όπως περιγράφονται στο system prompt.

Οι όψεις που θέλω να αναλύσεις είναι ΜΟΝΟ αυτές που υπάρχουν στη λίστα "aspects".
Για κάθε όψη γράψε ΜΙΑ ξεχωριστή παράγραφο, στην κατάλληλη υποενότητα.

{json.dumps(payload, ensure_ascii=False, indent=2)}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_per_aspect_report_with_openai(payload: dict, aspect_obj: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Θα λάβεις ένα ΠΛΗΡΕΣ JSON γενέθλιου χάρτη και μία ΣΥΓΚΕΚΡΙΜΕΝΗ όψη προς ανάλυση.

Η δουλειά σου:
1. Να δεις σε ποιον οίκο βρίσκεται ο κάθε πλανήτης της όψης.
2. Να δεις το ζώδιο της ακμής εκείνου του οίκου και τον κυβερνήτη του.
3. Να συνδυάσεις όλα αυτά για να γράψεις μια βαθιά, συγκεκριμένη ερμηνεία της όψης.

ΣΗΜΑΝΤΙΚΟ:
- Γράψε ΜΟΝΟ την ερμηνεία αυτής της όψης.
- ΜΗΝ γράψεις γενικές εισαγωγές, τίτλους, επικεφαλίδες.
- Ξεκίνα ΑΜΕΣΑ με την ανάλυση της όψης.
- 4-6 προτάσεις, ζεστό & θεραπευτικό ύφος.
- Χρησιμοποίησε συγκεκριμένα θέματα ζωής από τους οίκους."""

    aspect_desc = (
        f"{aspect_obj['p1_gr']} ({aspect_obj['p1']}) "
        f"{aspect_obj['aspect_label_gr']} "
        f"{aspect_obj['p2_gr']} ({aspect_obj['p2']})"
    )

    user_prompt = f"""Ολόκληρος ο χάρτης:
{json.dumps(payload, ensure_ascii=False, indent=2)}

Η όψη προς ανάλυση:
{aspect_desc}

Γράψε ΜΟΝΟ την ερμηνεία αυτής της όψης, χωρίς εισαγωγή ή τίτλο."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_all_aspects_separately(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."
    
    aspects_list = payload.get("aspects", [])
    if not aspects_list:
        return "Δεν υπάρχουν όψεις προς ανάλυση."
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(aspects_list)
    start_time = datetime.now()
    
    for idx, aspect_obj in enumerate(aspects_list):
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time = elapsed / (idx + 1) if idx > 0 else 5
        remaining = int(avg_time * (total - idx - 1))
        
        status_text.text(
            f"Αναλύω όψη {idx+1}/{total}: {aspect_obj['p1_gr']} - {aspect_obj['p2_gr']} "
            f"(~{remaining}s υπολειπόμενα)"
        )
        
        try:
            interp = generate_per_aspect_report_with_openai(payload, aspect_obj)
            header = f"**{aspect_obj['p1_gr']} {aspect_obj['aspect_label_gr']} {aspect_obj['p2_gr']}**"
            results.append(f"{header}\n\n{interp}\n")
        except Exception as e:
            results.append(f"⚠️ Σφάλμα στην όψη {aspect_obj['p1_gr']}-{aspect_obj['p2_gr']}: {e}\n")
        
        progress_bar.progress((idx + 1) / total)
    
    status_text.text("✅ Ολοκληρώθηκε!")
    return "\n---\n\n".join(results)


def generate_full_report_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."
    
    report_parts = []
    
    try:
        basic = generate_basic_report_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Α: ΒΑΣΙΚΗ ΑΝΑΦΟΡΑ (Ενότητες 0-3)")
        report_parts.append("=" * 80)
        report_parts.append(basic)
        report_parts.append("\n\n")
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στη βασική αναφορά: {e}\n\n")
    
    try:
        talents = generate_section4_report_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Β: ΤΑΛΕΝΤΑ & ΕΣΩΤΕΡΙΚΗ ΠΟΡΕΙΑ (Ενότητα 4)")
        report_parts.append("=" * 80)
        report_parts.append(talents)
        report_parts.append("\n\n")
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στην ενότητα 4: {e}\n\n")
    
    try:
        aspects = generate_section5_aspects_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Γ: ΑΝΑΛΥΤΙΚΕΣ ΟΨΕΙΣ (Ενότητα 5)")
        report_parts.append("=" * 80)
        report_parts.append(aspects)
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στην ενότητα 5: {e}\n\n")
    
    return "\n".join(report_parts)


# ============ PDF GENERATION (unchanged) ============
def create_pdf(payload: dict, report_text: str) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm)
    story = []

    base_font = "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        base_font = "DejaVuSans"
    except Exception:
        pass

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
        fontName=base_font, fontSize=16, textColor='#4A4A4A',
        spaceAfter=12, alignment=TA_CENTER)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'],
        fontName=base_font, fontSize=12, textColor='#2C3E50',
        spaceAfter=10, spaceBefore=10)
    body_style = ParagraphStyle('CustomBody', parent=styles['BodyText'],
        fontName=base_font, fontSize=10, leading=14, alignment=TA_LEFT)

    story.append(Paragraph("Προσωπική Έκθεση Γενέθλιου Χάρτη", title_style))
    story.append(Spacer(1, 0.5*cm))

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Δημιουργήθηκε: {date_str}", body_style))
    story.append(Spacer(1, 1*cm))

    basic = payload.get("basic_info", {})
    story.append(Paragraph("Βασικά Στοιχεία", heading_style))
    story.append(Paragraph(f"Ζώδιο Ηλίου: {basic.get('sun_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ωροσκόπος: {basic.get('asc_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ζώδιο Σελήνης: {basic.get('moon_sign_gr', 'N/A')}", body_style))
    story.append(Spacer(1, 1*cm))

    story.append(Paragraph("Αναλυτική Αναφορά", heading_style))
    for para in report_text.split('\n\n'):
        if para.strip():
            safe_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_para, body_style))
            story.append(Spacer(1, 0.3*cm))

    story.append(PageBreak())
    story.append(Paragraph("Τεχνικά Δεδομένα (JSON)", heading_style))
    json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    for line in json_str.split('\n')[:50]:
        safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(f"<font name=Courier size=8>{safe_line}</font>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ============ MAIN UI ============
def main():
    st.set_page_config(page_title="Γενέθλιος Χάρτης – Beta", layout="wide")
    st.title("🪷 Προσωπική Έκθεση Γενέθλιου Χάρτη – Beta (v2)")

    st.markdown("""
    Αυτό το εργαλείο σε βοηθά να διαβάζεις τον χάρτη από το astro.com 
    και να φτιάχνεις δομημένα δεδομένα για μια αναλυτική έκθεση με ChatGPT.
    
    **🆕 Βελτιώσεις v2:**
    - ✅ Collapsed sections για όψεις (91 selectboxes → συμπτυσσόμενα)
    - ✅ Validation warnings για ελλιπή δεδομένα
    - ✅ Caching OpenAI calls (γρηγορότερες επαναλήψεις)
    - ✅ Export σε JSON & Markdown
    - ✅ Estimated time για per-aspect analysis
    """)