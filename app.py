import os
import json
from io import BytesIO
from datetime import datetime
import streamlit as st
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase import ttfonts

# Use ttfonts.TTFont alias for safety in this environment
TTFont = ttfonts.TTFont

# ---------- ΡΥΘΜΙΣΕΙΣ / ΣΤΑΘΕΡΕΣ ----------

# Ζώδια: Ελληνικά -> Αγγλικά
SIGNS_GR_TO_EN = {
    "Κριός": "Aries",
    "Ταύρος": "Taurus",
    "Δίδυμοι": "Gemini",
    "Καρκίνος": "Cancer",
    "Λέων": "Leo",
    "Παρθένος": "Virgo",
    "Ζυγός": "Libra",
    "Σκορπιός": "Scorpio",
    "Τοξότης": "Sagittarius",
    "Αιγόκερως": "Capricorn",
    "Υδροχόος": "Aquarius",
    "Ιχθύες": "Pisces",
}

SIGNS_GR_LIST = list(SIGNS_GR_TO_EN.keys())
SIGNS_WITH_EMPTY = ["---"] + SIGNS_GR_LIST

# Κυβερνήτες ζωδίων (Αγγλικά)
SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Pluto",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",
    "Pisces": "Neptune",
}

# Αντίστροφος πίνακας: Αγγλικά -> Ελληνικά ονόματα πλανητών
PLANET_EN_TO_GR = {
    "Sun": "Ήλιος",
    "Moon": "Σελήνη",
    "Mercury": "Ερμής",
    "Venus": "Αφροδίτη",
    "Mars": "Άρης",
    "Jupiter": "Δίας",
    "Saturn": "Κρόνος",
    "Uranus": "Ουρανός",
    "Neptune": "Ποσειδώνας",
    "Pluto": "Πλούτωνας",
    "Chiron": "Χείρωνας",
    "North Node": "Βόρειος Δεσμός",
    "AC": "AC",
    "MC": "MC",
}

# Πλανήτες: (Ελληνικά, Αγγλικά)
PLANETS = [
    ("Ήλιος", "Sun"),
    ("Σελήνη", "Moon"),
    ("Ερμής", "Mercury"),
    ("Αφροδίτη", "Venus"),
    ("Άρης", "Mars"),
    ("Δίας", "Jupiter"),
    ("Κρόνος", "Saturn"),
    ("Ουρανός", "Uranus"),
    ("Ποσειδώνας", "Neptune"),
    ("Πλούτωνας", "Pluto"),
    ("Βόρειος Δεσμός", "North Node"),
    ("Χείρωνας", "Chiron"),
    ("AC", "AC"),
    ("MC", "MC"),
]

# Όψεις: label για UI -> κωδικός για JSON
ASPECT_OPTIONS = [
    ("Καμία", None),
    ("🔴 ☌ Σύνοδος (0°)", "conjunction"),
    ("🔴 ☍ Αντίθεση (180°)", "opposition"),
    ("🔵 △ Τρίγωνο (120°)", "trine"),
    ("🔴 □ Τετράγωνο (90°)", "square"),
    ("🔵 ⚹ Εξάγωνο (60°)", "sextile"),
]


def get_openai_client():
    """Φτιάχνει OpenAI client αν υπάρχει API key."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# ---------- OPENAI ΚΛΗΣΕΙΣ ----------

def generate_basic_report_with_openai(payload: dict) -> str:
    """
    Βασική αναφορά: Ενότητες 0–3 (κουτάκι + ακμές οίκων + πλανήτες/κυβερνήτες σε οίκους + όψεις).
    Χωρίς Ενότητα 4.
    """
    client = get_openai_client()
    if client is None:
        return (
            "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον.\n"
            "Ρύθμισέ το για να μπορεί να κληθεί αυτόματα το ChatGPT.\n"
            "Προς το παρόν μπορείς να κάνεις copy–paste το JSON στο ChatGPT χειροκίνητα."
        )

    system_prompt = (
        "Είσαι έμπειρη αστρολόγος.\n"
        "Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη: basic_info (Ήλιος, Ωροσκόπος, Σελήνη), houses, "
        "planets_in_houses και aspects.\n"
        "Θέλω να γράφεις ΠΑΝΤΑ σε καλή, καθαρή ελληνική γλώσσα.\n\n"
        "Να ακολουθείς αυτή τη δομή αναφοράς:\n"
        "0. Μικρό κουτάκι με βασικά στοιχεία (Ήλιος, Ωροσκόπος, Σελήνη).\n"
        "1. ΕΝΟΤΗΤΑ 1 – Οι ακμές των οίκων: για κάθε οίκο 1–12 μια σύντομη παράγραφο "
        "με θέμα οίκου + χρώμα ζωδίου ακμής.\n"
        "2. ΕΝΟΤΗΤΑ 2 – Πλανήτες & κυβερνήτες σε οίκους: για κάθε οίκο, αν έχει πλανήτες "
        "γράψε ανάλυση. Αν δεν έχει, εξήγησε τον οίκο μέσω του ζωδίου της ακμής και του "
        "κυβερνήτη του ζωδίου (πλανήτης και οίκος στον οποίο βρίσκεται). "
        "Το JSON περιέχει τα πεδία 'ruler' (ποιος πλανήτης κυβερνά το ζώδιο) και "
        "'ruler_in_house' (σε ποιον οίκο βρίσκεται ο κυβερνήτης, ή null αν δεν υπάρχει).\n"
        "3. ΕΝΟΤΗΤΑ 3 – Όψεις:\n"
        "- Για ΚΑΘΕ όψη που υπάρχει στο JSON να γράφεις ξεχωριστά, χωρίς να τις συγχωνεύεις όλες σε μία γενική παράγραφο.\n"
        "- Για κάθε ζευγάρι πλανητών, εξήγησε με 1–2 μικρές παραγράφους τη δυναμική "
        "της όψης (π.χ. συνεργασία, ένταση, εσωτερική σύγκρουση, ταλέντο που χρειάζεται "
        "δουλειά κ.λπ.).\n"
        "- Αν οι όψεις είναι πολλές (πάνω από 12), δώσε μεγαλύτερη ανάλυση στις πιο "
        "σημαντικές (Ήλιος, Σελήνη, Ωροσκόπος, προσωπικοί πλανήτες) και για τις πιο "
        "δευτερεύουσες μπορείς να γράφεις πιο σύντομα (2–3 προτάσεις).\n"
        "- Όψεις που ΔΕΝ υπάρχουν στο JSON, αγνόησέ τες.\n\n"
        "ΓΕΝΙΚΕΣ ΟΔΗΓΙΕΣ ΥΦΟΥΣ ΓΙΑ ΟΛΕΣ ΤΙΣ ΕΝΟΤΗΤΕΣ:\n"
        "- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.\n"
        "- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό. Όχι μοιρολατρικό.\n"
        "- Μη χρησιμοποιείς τεχνική ορολογία χωρίς εξήγηση.\n"
        "- Μην αναφέρεις μοίρες, όψεις ή πολύ δύσκολους όρους αν δεν είναι απαραίτητο.\n"
        "- Μην επαναλαμβάνεις αυτούσια τα προηγούμενα κείμενα. Χτίσε πάνω τους.\n"
        "- Μη μιλάς για καλό/κακό χάρτη. Μίλα για δυνατότητες, προκλήσεις και εξέλιξη.\n\n"
        "Η γλώσσα να είναι ζεστή αλλά όχι υπερβολικά 'ποιητική'. Να είναι σαφής, "
        "παιδαγωγική και ενδυναμωτική."
    )

    user_prompt = (
        "Παρακάτω είναι τα δεδομένα του χάρτη σε JSON.\n"
        "Να γράψεις την Προσωπική Έκθεση Γενέθλιου Χάρτη ΜΟΝΟ για τις Ενότητες 0–3 "
        "(βασικά στοιχεία, ακμές οίκων, πλανήτες/κυβερνήτες σε οίκους, όψεις), "
        "όπως περιγράφονται στο system prompt.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_section4_report_with_openai(payload: dict) -> str:
    """
    Μόνο Ενότητα 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία (4.1–4.5).
    Χρησιμοποιεί όλο το JSON ως πλαίσιο.
    """
    client = get_openai_client()
    if client is None:
        return (
            "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον.\n"
            "Ρύθμισέ το για να μπορεί να κληθεί αυτόματα το ChatGPT.\n"
            "Προς το παρόν μπορείς να κάνεις copy–paste το JSON στο ChatGPT χειροκίνητα."
        )

    system_prompt = (
        "Είσαι έμπειρη αστρολόγος.\n"
        "Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη: basic_info (Ήλιος, Ωροσκόπος, Σελήνη), houses, "
        "planets_in_houses και aspects.\n"
        "Με βάση αυτά, θέλω να γράψεις ΜΟΝΟ την ΕΝΟΤΗΤΑ 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία.\n\n"
        "4. ΕΝΟΤΗΤΑ 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία\n"
        "Δίαιρεσε την ενότητα στις παρακάτω υποενότητες, με ακριβώς αυτούς τους τίτλους και αρίθμηση:\n\n"
        "4.1 Κύρια Ταλέντα & Δυνατά Σημεία\n"
        "– Περιέγραψε τα βασικά ταλέντα και ψυχικές δυνάμεις του ατόμου, βασισμένα κυρίως:\n"
        "  * στο ζώδιο Ήλιου,\n"
        "  * στο ζώδιο Σελήνης και τον οίκο της,\n"
        "  * στον Ωροσκόπο,\n"
        "  * στη θέση των πλανητών στους οίκους,\n"
        "  * σε έντονες συγκεντρώσεις πλανητών (π.χ. πολλοί στον 11ο κ.λπ.).\n"
        "– Να είναι πρακτικό, κατανοητό και ζεστό, σε ύφος θεραπευτικό και ενδυναμωτικό.\n\n"
        "4.2 Επαγγέλματα & Κατευθύνσεις που ταιριάζουν συμβολικά\n"
        "– Δώσε ενδεικτικές επαγγελματικές κατευθύνσεις που ταιριάζουν στο άτομο με βάση τον χάρτη.\n"
        "– Τόνισε ότι δεν είναι “προφητεία” αλλά συμβολικές κατευθύνσεις που κουμπώνουν με τα ταλέντα του.\n"
        "– Σύνδεσε τις επιλογές με Ήλιο, Σελήνη, Ωροσκόπο και δυνατούς οίκους (10ος, 6ος, 11ος κ.λπ.).\n\n"
        "4.3 Ταλέντα που ίσως έχει “ξεχάσει” ότι έχει\n"
        "– Περιέγραψε ικανότητες και κλίσεις που πιθανόν το άτομο να υποτιμά ή να έχει αφήσει στην άκρη.\n"
        "– Μπορείς να χρησιμοποιήσεις στοιχεία από 12ο οίκο, 8ο οίκο, Ποσειδώνα, Ουρανό, Πλούτωνα κ.λπ.\n"
        "– Στόχος: να του θυμίσεις κομμάτια του εαυτού του που αξίζει να ξαναφέρει στη ζωή του.\n\n"
        "4.4 Πώς μπορεί να ξαναβρεί τον “χαμένο” του εαυτό\n"
        "– Δώσε συγκεκριμένες, ήπιες, πρακτικές προτάσεις:\n"
        "  * τι το βοηθά να συνδεθεί με τον αληθινό του εαυτό,\n"
        "  * τι είδους σχέσεις, δραστηριότητες ή project το τροφοδοτούν.\n"
        "– Χρησιμοποίησε ιδιαίτερα τον Βόρειο Δεσμό (North Node) και τον 8ο/9ο/12ο οίκο όπου είναι σχετικό.\n\n"
        "4.5 Τι είναι καλό να προσέχει\n"
        "– Περιέγραψε “παγίδες” του χάρτη:\n"
        "  * π.χ. υπερ-ανάλυση, υπερ-ευθύνη, διασπορά ενέργειας, ρόλος “σωτήρα” κ.λπ.\n"
        "– Να ΜΗΝ είναι φοβιστικό ή καταστροφικό. Να είναι προειδοποιητικό, αλλά πάντα με τόνο:\n"
        "  “πώς μπορείς να το δουλέψεις προς όφελός σου”.\n\n"
        "ΓΕΝΙΚΕΣ ΟΔΗΓΙΕΣ ΥΦΟΥΣ:\n"
        "- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.\n"
        "- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό. Όχι μοιρολατρικό.\n"
        "- Μη χρησιμοποιείς τεχνική ορολογία χωρίς εξήγηση.\n"
        "- Μην αναφέρεις μοίρες, όψεις ή πολύ δύσκολους όρους αν δεν είναι απαραίτητο.\n"
        "- Μην επαναλαμβάνεις αυτούσια τα προηγούμενα κείμενα. Χτίσε πάνω τους.\n"
        "- Μη μιλάς για “καλό/κακό χάρτη”. Μίλα για δυνατότητες, προκλήσεις και εξέλιξη.\n\n"
        "Η γλώσσα να είναι ζεστή αλλά όχι υπερβολικά 'ποιητική'. Να είναι σαφής, "
        "παιδαγωγική και ενδυναμωτική."
    )

    user_prompt = (
        "Παρακάτω είναι τα δεδομένα του χάρτη σε JSON.\n"
        "Χρησιμοποίησέ τα για να γράψεις ΜΟΝΟ την Ενότητα 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία "
        "με τις υποενότητες 4.1–4.5 όπως περιγράφονται στο system prompt.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ---------- PDF ----------

def create_pdf(payload: dict, report_text: str) -> BytesIO:
    """Δημιουργεί PDF με JSON δεδομένα και αναφορά."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm)
    story = []

    # Unicode font
    base_font = "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        base_font = "DejaVuSans"
    except Exception:
        pass

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=base_font,
        fontSize=16,
        textColor='#4A4A4A',
        spaceAfter=12,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=base_font,
        fontSize=12,
        textColor='#2C3E50',
        spaceAfter=10,
        spaceBefore=10
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontName=base_font,
        fontSize=10,
        leading=14,
        alignment=TA_LEFT
    )

    # Τίτλος
    story.append(Paragraph("Προσωπική Έκθεση Γενέθλιου Χάρτη", title_style))
    story.append(Spacer(1, 0.5*cm))

    # Ημερομηνία
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    story.append(Paragraph(f"Δημιουργήθηκε: {date_str}", body_style))
    story.append(Spacer(1, 1*cm))

    # Βασικά στοιχεία
    basic = payload.get("basic_info", {})
    story.append(Paragraph("Βασικά Στοιχεία", heading_style))
    story.append(Paragraph(f"Ζώδιο Ήλιου: {basic.get('sun_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ωροσκόπος: {basic.get('asc_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ζώδιο Σελήνης: {basic.get('moon_sign_gr', 'N/A')}", body_style))
    story.append(Spacer(1, 1*cm))

    # Αναφορά
    story.append(Paragraph("Αναλυτική Αναφορά", heading_style))
    for para in report_text.split('\n\n'):
        if para.strip():
            safe_para = (
                para.replace('&', '&amp;')
                    .replace('<', '&lt;')
                    .replace('>', '&gt;')
            )
            story.append(Paragraph(safe_para, body_style))
            story.append(Spacer(1, 0.3*cm))

    # JSON data (προαιρετικά, πρώτο μέρος)
    story.append(PageBreak())
    story.append(Paragraph("Τεχνικά Δεδομένα (JSON)", heading_style))
    json_str = json.dumps(payload, ensure_ascii=False, indent=2)
    for line in json_str.split('\n')[:50]:
        safe_line = (
            line.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
        )
        story.append(Paragraph(f"<font name=Courier size=8>{safe_line}</font>", body_style))

    doc.build(story)
    buffer.seek(0)
    return buffer


# ---------- UI STREAMLIT ----------

def main():
    st.set_page_config(page_title="Γενέθλιος Χάρτης – Beta", layout="wide")
    st.title("🪷 Προσωπική Έκθεση Γενέθλιου Χάρτη – Beta")

    st.markdown(
        "Αυτό το εργαλείο σε βοηθά να διαβάζεις τον χάρτη από το astro.com "
        "και να φτιάχνεις δομημένα δεδομένα για μια αναλυτική έκθεση με ChatGPT."
    )

    # Session state
    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    if "prev_asc" not in st.session_state:
        st.session_state.prev_asc = None

    # ----- ΒΑΣΙΚΑ ΣΤΟΙΧΕΙΑ -----
    st.header("0. Βασικά στοιχεία χάρτη")

    col1, col2, col3 = st.columns(3)
    with col1:
        sun_sign_gr = st.selectbox(
            "Ζώδιο Ήλιου",
            SIGNS_WITH_EMPTY,
            index=0,
            key=f"sun_sign_{st.session_state.reset_counter}",
        )
    with col2:
        asc_sign_gr = st.selectbox(
            "Ωροσκόπος",
            SIGNS_WITH_EMPTY,
            index=0,
            key=f"asc_sign_{st.session_state.reset_counter}",
        )
    with col3:
        moon_sign_gr = st.selectbox(
            "Ζώδιο Σελήνης",
            SIGNS_WITH_EMPTY,
            index=0,
            key=f"moon_sign_{st.session_state.reset_counter}",
        )

    # ----- ΟΙΚΟΙ -----
    st.header("1. Ενότητα 1 – Ακμές οίκων (ζώδιο σε κάθε οίκο)")
    st.markdown("Διάβασε από τον χάρτη σου σε ποιο ζώδιο ξεκινά κάθε οίκος (1–12) και διάλεξέ το.")

    houses_signs_gr = {}
    # Συγχρονισμός Οίκου 1 με τον Ωροσκόπο
    house1_key = f"house_1_{st.session_state.reset_counter}"
    if asc_sign_gr in SIGNS_WITH_EMPTY:
        st.session_state[house1_key] = asc_sign_gr
    else:
        st.session_state[house1_key] = SIGNS_WITH_EMPTY[0]

    cols = st.columns(4)
    for i in range(1, 13):
        col = cols[(i - 1) % 4]
        with col:
            if i == 1:
                sign = st.selectbox(
                    "Οίκος 1 (ίδιος με Ωροσκόπο)",
                    SIGNS_WITH_EMPTY,
                    key=house1_key,
                    disabled=True,
                )
            else:
                sign = st.selectbox(
                    f"Οίκος {i}",
                    SIGNS_WITH_EMPTY,
                    key=f"house_{i}_{st.session_state.reset_counter}",
                )
        houses_signs_gr[i] = sign

    # ----- ΠΛΑΝΗΤΕΣ -----
    st.header("2. Ενότητα 2 – Πλανήτες σε οίκους")
    st.markdown(
        "Για κάθε οίκο (1–12), διάλεξε ποιοι πλανήτες/Χείρωνας/Βόρειος Δεσμός/AC/MC βρίσκονται μέσα σε αυτόν τον οίκο.\n"
        "Αν ο οίκος δεν έχει κανέναν, τικάρισε μόνο το 'Κανένας'."
    )

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

            available_planets = ["Κανένας"] + [
                p for p in planet_names_gr if p not in already_selected
            ]

            selected_planets_gr = st.multiselect(
                f"Πλανήτες στον Οίκο {i}",
                available_planets,
                key=f"house_planets_{i}_{st.session_state.reset_counter}",
            )
        house_planets_map[i] = selected_planets_gr

    # Build planet_house_map
    planet_house_map = {}
    for house_num, planets_gr_list in house_planets_map.items():
        if "Κανένας" in planets_gr_list or len(planets_gr_list) == 0:
            continue
        for gr_name in planets_gr_list:
            if gr_name == "Κανένας":
                continue
            en_name = next(en for (gr, en) in PLANETS if gr == gr_name)
            planet_house_map[en_name] = house_num

    # ----- ΌΨΕΙΣ -----
    st.header("3. Ενότητα 3 – Όψεις ανάμεσα σε πλανήτες")
    st.markdown(
        "Για κάθε ζευγάρι πλανητών, αν υπάρχει σημαντική όψη, διάλεξε τη μορφή της. "
        "Αν δεν υπάρχει ή δεν θες να την ερμηνεύσεις, άφησέ το 'Καμία'."
    )

    aspect_labels = [opt[0] for opt in ASPECT_OPTIONS]
    label_to_code = {opt[0]: opt[1] for opt in ASPECT_OPTIONS}

    aspects_selected_ui = {}
    for i, (gr1, en1) in enumerate(PLANETS):
        if gr1 in ("AC", "MC"):
            continue
        st.markdown(f"#### Όψεις {gr1}")
        for j in range(i + 1, len(PLANETS)):
            gr2, en2 = PLANETS[j]
            key = f"aspect_{en1}_{en2}_{st.session_state.reset_counter}"
            choice = st.selectbox(
                f"{gr1} – {gr2}",
                aspect_labels,
                key=key,
            )
            aspects_selected_ui[(en1, en2)] = choice

    # ----- ΚΟΥΜΠΙΑ ΑΝΑΦΟΡΑΣ -----
    st.markdown("---")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        basic_button = st.button("📝 Βασική αναφορά (Ενότητες 0–3)")
    with col_b2:
        talents_button = st.button("🌟 Ενότητα 4 – Ταλέντα & Θεραπευτική Πορεία")

    if basic_button or talents_button:
        # Έλεγχος βασικών
        if sun_sign_gr == "---" or asc_sign_gr == "---" or moon_sign_gr == "---":
            st.error("⚠️ Παρακαλώ συμπλήρωσε Ζώδιο Ήλιου, Ωροσκόπο και Ζώδιο Σελήνης!")
            return

        # Φτιάχνουμε payload ΜΙΑ φορά
        basic_info = {
            "sun_sign_gr": sun_sign_gr,
            "sun_sign": SIGNS_GR_TO_EN[sun_sign_gr],
            "asc_sign_gr": asc_sign_gr,
            "asc_sign": SIGNS_GR_TO_EN[asc_sign_gr],
            "moon_sign_gr": moon_sign_gr,
            "moon_sign": SIGNS_GR_TO_EN[moon_sign_gr],
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
                "house": house_num,
                "sign_gr": sign_gr,
                "sign": sign_en,
                "ruler": ruler_en,
                "ruler_gr": ruler_gr,
                "ruler_in_house": ruler_in_house,
            })

        planets_in_houses = []
        for en_name, house_num in planet_house_map.items():
            gr_name = next(gr for gr, en in PLANETS if en == en_name)
            planets_in_houses.append({
                "planet": en_name,
                "planet_gr": gr_name,
                "house": house_num,
            })

        aspects = []
        for (p1, p2), label in aspects_selected_ui.items():
            code = label_to_code.get(label)
            if code is None:
                continue
            gr1 = next(gr for gr, en in PLANETS if en == p1)
            gr2 = next(gr for gr, en in PLANETS if en == p2)
            aspects.append({
                "p1": p1,
                "p1_gr": gr1,
                "p2": p2,
                "p2_gr": gr2,
                "aspect": code,
                "aspect_label_gr": label,
            })

        payload = {
            "basic_info": basic_info,
            "houses": houses,
            "planets_in_houses": planets_in_houses,
            "aspects": aspects,
        }

        st.subheader("🔍 JSON δεδομένων χάρτη (είσοδος προς ChatGPT)")
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

        # Ανάλογα με το κουμπί, καλούμε διαφορετικό prompt
        if basic_button:
            st.subheader("🤖 Βασική αναφορά με OpenAI (Ενότητες 0–3)")
            with st.spinner("Καλώ το μοντέλο για τη βασική αναφορά..."):
                try:
                    report_text = generate_basic_report_with_openai(payload)
                except Exception as e:
                    report_text = f"Παρουσιάστηκε σφάλμα κατά την κλήση του OpenAI API:\n{e}"

            st.markdown("### 📜 Αναφορά (Ενότητες 0–3)")
            st.write(report_text)

            st.markdown("---")
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button(
                label="📄 Λήψη Βασικής Αναφοράς σε PDF",
                data=pdf_buffer,
                file_name=f"basic_genethlio_xarth_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

        if talents_button:
            st.subheader("🤖 Αναφορά Ενότητας 4 με OpenAI")
            with st.spinner("Καλώ το μοντέλο μόνο για την Ενότητα 4..."):
                try:
                    report_text = generate_section4_report_with_openai(payload)
                except Exception as e:
                    report_text = f"Παρουσιάστηκε σφάλμα κατά την κλήση του OpenAI API:\n{e}"

            st.markdown("### 📜 Ενότητα 4 – Ταλέντα, Δυνατότητες & Εσωτερική Πορεία")
            st.write(report_text)

            st.markdown("---")
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button(
                label="📄 Λήψη Αναφοράς Ενότητας 4 σε PDF",
                data=pdf_buffer,
                file_name=f"section4_genethlio_xarth_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )

    # ----- ΕΠΑΝΕΚΚΙΝΗΣΗ -----
    st.markdown("---")
    if st.button("🔄 Επανεκκίνηση (μηδενισμός όλων των δεδομένων)"):
        st.session_state.reset_counter += 1
        st.rerun()


if __name__ == "__main__":
    main()
