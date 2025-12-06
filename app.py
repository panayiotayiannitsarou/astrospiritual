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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============ CONSTANTS ============
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


def get_neighboring_signs(sign_gr: str):
    """Return [previous_sign, same_sign, next_sign] for a given Greek sign name."""
    if sign_gr not in SIGNS_GR_LIST:
        return SIGNS_GR_LIST[:3]
    idx = SIGNS_GR_LIST.index(sign_gr)
    prev_sign = SIGNS_GR_LIST[(idx - 1) % len(SIGNS_GR_LIST)]
    next_sign = SIGNS_GR_LIST[(idx + 1) % len(SIGNS_GR_LIST)]
    return [prev_sign, sign_gr, next_sign]


# ============ UTILITIES ============
def get_openai_client() -> Optional[OpenAI]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except:
            pass
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
    
    houses = payload.get("houses", [])
    if len(houses) < 12:
        warnings.append(f"⚠️ Μόνο {len(houses)}/12 οίκοι συμπληρωμένοι")
    
    planets_placed = payload.get("planets_in_houses", [])
    placed_planet_names = {p["planet"] for p in planets_placed}
    
    expected_planets = {en for (gr, en) in PLANETS if en not in ("AC", "MC")}
    missing_planets = expected_planets - placed_planet_names
    
    if missing_planets:
        missing_gr = [PLANET_EN_TO_GR.get(en, en) for en in sorted(missing_planets)]
        warnings.append(
            f"⚠️ Λείπουν πλανήτες: {', '.join(missing_gr)} "
            f"({len(placed_planet_names)}/{len(expected_planets)} τοποθετημένοι)"
        )
    
    aspects = payload.get("aspects", [])
    if len(aspects) == 0:
        warnings.append("⚠️ Καμία όψη επιλεγμένη")
    elif len(aspects) < 5:
        warnings.append(f"ℹ️ Μόνο {len(aspects)} όψεις (συνιστώνται τουλάχιστον 5-10)")
    
    return warnings


# ============ OPENAI FUNCTION (CACHED) ============
@st.cache_data(show_spinner=False)
def generate_basic_report_cached(payload_hash: str, payload: dict) -> str:
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

1. ΕΝΟΤΗΤΑ 1 – Οι ακμές των οίκων
- Για κάθε οίκο 1–12 γράψε μια σύντομη παράγραφο που να συνδέει:
  • το θέμα του οίκου (π.χ. 7ος = σχέσεις, γάμος),
  • με το ζώδιο της ακμής του οίκου,
  • και, όπου ταιριάζει, με τον κυβερνήτη αυτού του ζωδίου.

2. ΕΝΟΤΗΤΑ 2 – Πλανήτες & κυβερνήτες σε οίκους
- Για κάθε οίκο:
  • Αν έχει μέσα πλανήτες, γράψε ανάλυση για το πώς εκφράζονται αυτοί οι πλανήτες μέσα από τα θέματα του οίκου.
  • Αν δεν έχει πλανήτες, εξήγησε τον οίκο μέσω:
    — του ζωδίου της ακμής και
    — του κυβερνήτη του ζωδίου (σε ποιον οίκο βρίσκεται και τι σημαίνει αυτό).

3. ΕΝΟΤΗΤΑ 3 – Όψεις ανάμεσα σε πλανήτες (δομή με αριθμούς)
Γράψε τις όψεις οργανωμένα σε υποενότητες, με αριθμημένες γραμμές όπως στο παράδειγμα:

3.1 Όψεις Ηλίου
- Συμπερίλαβε μόνο τις όψεις που έχουν τον Ήλιο (Sun) ΚΑΙ υπάρχουν στη λίστα "aspects" του JSON.
- Γράψε τες αριθμημένα, με μορφή:
  1. Ήλιος – Σελήνη: [3-4 προτάσεις ερμηνείας]
  2. Ήλιος – Ερμής: [3-4 προτάσεις ερμηνείας]
  κ.ο.κ., αλλά ΜΟΝΟ για τα ζευγάρια που πραγματικά εμφανίζονται στις "aspects".

3.2 Όψεις Σελήνης
- Αντίστοιχα, βάλε εδώ όλες τις όψεις που έχουν τη Σελήνη (Moon) και υπάρχουν στο JSON.
- Γράψε τες αριθμημένα:
  1. Σελήνη – Ερμής: [ερμηνεία]
  2. Σελήνη – Αφροδίτη: [ερμηνεία]
  κ.ο.κ.

3.3 Όψεις υπόλοιπων πλανητών
- Εδώ βάζεις, με την ίδια λογική, τις όψεις των υπόλοιπων πλανητών.
- Ομαδοποίησέ τες ανά πλανήτη, π.χ.:
  • Όψεις Ερμή
    1. Ερμής – Αφροδίτη: [ερμηνεία]
    2. Ερμής – Άρης: [ερμηνεία]
- Αν κάποιος πλανήτης δεν έχει καμία όψη στο JSON, μπορείς να παραλείψεις την υποενότητά του.
- ΜΗΝ εφευρίσκεις επιπλέον όψεις· χρησιμοποίησε μόνο όσες υπάρχουν στη λίστα "aspects".

ΓΕΝΙΚΕΣ ΟΔΗΓΙΕΣ ΥΦΟΥΣ:
- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.
- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό. Όχι μοιρολατρικό.
- Μη χρησιμοποιείς τεχνική ορολογία χωρίς εξήγηση.
- Μη μιλάς για καλό/κακό χάρτη. Μίλα για δυνατότητες, προκλήσεις και εξέλιξη."""

    user_prompt = f"""Παρακάτω είναι τα δεδομένα του χάρτη σε JSON.
Να γράψεις την Προσωπική Έκθεση Γενέθλιου Χάρτη με όλες τις Ενότητες 0–3.

{json.dumps(payload, ensure_ascii=False, indent=2)}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ============ PDF GENERATION ============
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

    doc.build(story)
    buffer.seek(0)
    return buffer


# ============ MAIN UI ============
def main():
    st.set_page_config(page_title="Γενέθλιος Χάρτης", layout="wide")
    st.title("🪷 Προσωπική Έκθεση Γενέθλιου Χάρτη")

    st.markdown("""
    **✨ Απλοποιημένη Έκδοση:**
    - ✅ **Caching** για γρήγορη επανάληψη
    - ✅ **Validation** warnings για ελλιπή δεδομένα
    - ✅ **Αριθμημένες όψεις** στο UI
    - ✅ **1 κουμπί** – Πλήρης αναφορά με Ενότητες 0-3
    """)

    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0

    # ============ SECTION 0: BASIC INFO ============
    st.header("0. Βασικά στοιχεία χάρτη")
    col1, col2, col3 = st.columns(3)
    with col1:
        sun_sign_gr = st.selectbox("Ζώδιο Ηλίου", SIGNS_WITH_EMPTY, index=0,
            key=f"sun_sign_{st.session_state.reset_counter}")
    with col2:
        asc_sign_gr = st.selectbox("Ωροσκόπος", SIGNS_WITH_EMPTY, index=0,
            key=f"asc_sign_{st.session_state.reset_counter}")
    with col3:
        moon_sign_gr = st.selectbox("Ζώδιο Σελήνης", SIGNS_WITH_EMPTY, index=0,
            key=f"moon_sign_{st.session_state.reset_counter}")

    # ============ SECTION 1: HOUSES ============
    st.header("1. Ενότητα 1 – Ακμές οίκων")
    st.markdown("Διάβασε από τον χάρτη σου σε ποιο ζώδιο ξεκινά κάθε οίκος (1–12).")

    houses_signs_gr = {}
    house1_key = f"house_1_{st.session_state.reset_counter}"
    st.session_state[house1_key] = asc_sign_gr if asc_sign_gr in SIGNS_WITH_EMPTY else SIGNS_WITH_EMPTY[0]

    cols = st.columns(4)
    for i in range(1, 13):
        col = cols[(i - 1) % 4]
        with col:
            if i == 1:
                sign = st.selectbox("Οίκος 1 (ίδιος με Ωροσκόπο)", SIGNS_WITH_EMPTY,
                    key=house1_key, disabled=True)
            else:
                sign = st.selectbox(f"Οίκος {i}", SIGNS_WITH_EMPTY,
                    key=f"house_{i}_{st.session_state.reset_counter}")
        houses_signs_gr[i] = sign

    # ============ SECTION 2: PLANETS IN HOUSES ============
    st.header("2. Ενότητα 2 – Πλανήτες σε οίκους")
    st.markdown("Για κάθε οίκο, διάλεξε ποιοι πλανήτες βρίσκονται μέσα.")

    planet_names_gr = [gr for gr, en in PLANETS if gr not in ('AC', 'MC')]
    house_planets_map = {}
    cols_h2 = st.columns(4)

    for i in range(1, 13):
        col = cols_h2[(i - 1) % 4]
        with col:
            already_selected = []
            for prev_house in range(1, i):
                if prev_house in house_planets_map:
                    already_selected.extend(house_planets_map[prev_house])

            available_planets = [p for p in planet_names_gr if p not in already_selected]
            selected_planets_gr = st.multiselect(
                f"Πλανήτες στον Οίκο {i}",
                available_planets,
                key=f"house_planets_{i}_{st.session_state.reset_counter}",
            )
        house_planets_map[i] = selected_planets_gr

    planet_house_map = {}
    for house_num, planets_gr_list in house_planets_map.items():
        for gr_name in planets_gr_list:
            en_name = next(en for (gr, en) in PLANETS if gr == gr_name)
            planet_house_map[en_name] = house_num

    st.markdown("#### Ζώδιο κάθε πλανήτη μέσα στον οίκο του")
    st.markdown("Για κάθε πλανήτη, διάλεξε το ζώδιο του (προηγούμενο/ίδιο/επόμενο από την ακμή).")

    planet_sign_map = {}
    for gr_name, en_name in [(gr, en) for (gr, en) in PLANETS if en in planet_house_map]:
        house_num = planet_house_map[en_name]
        cusp_sign_gr = houses_signs_gr.get(house_num, "---")
        label = f"Ζώδιο για {gr_name} στον Οίκο {house_num}"

        if cusp_sign_gr in SIGNS_GR_LIST:
            prev_sign, mid_sign, next_sign = get_neighboring_signs(cusp_sign_gr)
            options = [prev_sign, mid_sign, next_sign]
            default_index = 1
        else:
            options = SIGNS_WITH_EMPTY
            default_index = 0

        selected_sign_gr = st.selectbox(
            label,
            options,
            index=default_index,
            key=f"planet_sign_{en_name}_house_{house_num}_{st.session_state.reset_counter}",
        )

        if selected_sign_gr in SIGNS_GR_TO_EN:
            planet_sign_map[en_name] = {
                "sign_gr": selected_sign_gr,
                "sign": SIGNS_GR_TO_EN[selected_sign_gr],
            }
        else:
            planet_sign_map[en_name] = {"sign_gr": None, "sign": None}

    # ============ SECTION 3: ASPECTS ============
    st.header("3. Ενότητα 3 – Όψεις ανάμεσα σε πλανήτες")
    st.markdown("💡 **Tip:** Κάντε κλικ στο βέλος για να ανοίξετε κάθε ομάδα όψεων.")

    aspect_labels = [opt[0] for opt in ASPECT_OPTIONS]
    label_to_code = {opt[0]: opt[1] for opt in ASPECT_OPTIONS}

    aspects_selected_ui = {}
    
    for i, (gr1, en1) in enumerate(PLANETS):
        if gr1 in ("AC", "MC"):
            continue
        
        with st.expander(f"**Όψεις {gr1}** 🔽", expanded=False):
            pair_index = 1
            
            for j in range(i + 1, len(PLANETS)):
                gr2, en2 = PLANETS[j]
                label_text = f"**{pair_index}.** {gr1} — {gr2}"
                key = f"aspect_{en1}_{en2}_{st.session_state.reset_counter}"
                
                choice = st.selectbox(
                    label_text, 
                    aspect_labels, 
                    key=key
                )
                aspects_selected_ui[(en1, en2)] = choice
                pair_index += 1

    # ============ ACTION BUTTON ============
    st.markdown("---")
    st.subheader("📊 Δημιουργία Αναφοράς")
    
    generate_button = st.button("📝 Δημιουργία Βασικής Αναφοράς (Ενότητες 0–3)", type="primary")

    # ============ PROCESSING ============
    if generate_button:
        if sun_sign_gr == "---" or asc_sign_gr == "---" or moon_sign_gr == "---":
            st.error("⚠️ Παρακαλώ συμπλήρωσε Ζώδιο Ηλίου, Ωροσκόπο και Ζώδιο Σελήνης!")
            return

        basic_info = {
            "sun_sign_gr": sun_sign_gr, "sun_sign": SIGNS_GR_TO_EN[sun_sign_gr],
            "asc_sign_gr": asc_sign_gr, "asc_sign": SIGNS_GR_TO_EN[asc_sign_gr],
            "moon_sign_gr": moon_sign_gr, "moon_sign": SIGNS_GR_TO_EN[moon_sign_gr],
        }

        houses = []
        for house_num, sign_gr in houses_signs_gr.items():
            if sign_gr == "---":
                continue
            sign_en = SIGNS_GR_TO_EN[sign_gr]
            ruler_en = SIGN_RULERS.get(sign_en)
            ruler_gr = PLANET_EN_TO_GR.get(ruler_en, ruler_en) if ruler_en else None
            ruler_in_house = planet_house_map.get(ruler_en)
            houses.append({
                "house": house_num, "sign_gr": sign_gr, "sign": sign_en,
                "ruler": ruler_en, "ruler_gr": ruler_gr, "ruler_in_house": ruler_in_house,
            })

        planets_in_houses = []
        for en_name, house_num in planet_house_map.items():
            gr_name = next(gr for gr, en in PLANETS if en == en_name)
            sign_info = planet_sign_map.get(en_name, {})
            planets_in_houses.append(
                {
                    "planet": en_name,
                    "planet_gr": gr_name,
                    "house": house_num,
                    "sign_gr": sign_info.get("sign_gr"),
                    "sign": sign_info.get("sign"),
                }
            )

        aspects = []
        for (p1, p2), label in aspects_selected_ui.items():
            code = label_to_code.get(label)
            if code is None:
                continue
            gr1 = next(gr for gr, en in PLANETS if en == p1)
            gr2 = next(gr for gr, en in PLANETS if en == p2)
            aspects.append({
                "p1": p1, "p1_gr": gr1, "p2": p2, "p2_gr": gr2,
                "aspect": code, "aspect_label_gr": label,
            })

        payload = {
            "basic_info": basic_info,
            "houses": houses,
            "planets_in_houses": planets_in_houses,
            "aspects": aspects,
        }

        warnings = validate_chart_data(payload)
        if warnings:
            st.warning("### ⚠️ Προειδοποιήσεις")
            for warning in warnings:
                st.markdown(f"- {warning}")
            st.markdown("---")

        with st.expander("📋 JSON δεδομένων χάρτη", expanded=False):
            st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

        payload_hash = compute_payload_hash(payload)

        st.subheader("🤖 Βασική Αναφορά με OpenAI")
        with st.spinner("⏳ Καλώ το μοντέλο... (με caching)"):
            try:
                report_text = generate_basic_report_cached(payload_hash, payload)
            except Exception as e:
                report_text = f"Σφάλμα: {e}"
        
        st.markdown("### 📜 Αναφορά Γενέθλιου Χάρτη (Ενότητες 0–3)")
        st.write(report_text)
        st.markdown("---")
        
        pdf_buffer = create_pdf(payload, report_text)
        st.download_button(
            "📄 Λήψη Αναφοράς σε PDF", 
            data=pdf_buffer,
            file_name=f"astro_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )
        st.success("✅ Η αναφορά ολοκληρώθηκε!")

    st.markdown("---")
    if st.button("🔄 Επανεκκίνηση (μηδενισμός όλων)"):
        st.session_state.reset_counter += 1
        st.rerun()
    
    st.caption("💡 **Tip:** Το caching εξοικονομεί χρόνο & κόστος στις επαναλήψεις.")


if __name__ == "__main__":
    main()
