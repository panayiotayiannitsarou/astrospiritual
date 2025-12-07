    # ============ QUESTIONS PROCESSING ============
    if generate_questions:
        if st.session_state.basic_report is None:
            st.error("⚠️ Πρέπει πρώτα να δημιουργήσεις τη Βασική Αναφορά!")
            st.info("👆 Πάτησε το κουμπί 'Δημιουργία Βασικής Αναφοράς' πρώτα.")
            return
        
        st.subheader("💎 Επιλογή Ερωτήσεων")
        st.markdown("**Α) Προκαθορισμένες Ερωτήσεις** - Διάλεξε όσες σε ενδιαφέρουν:")
        
        selected_questions = []
        for key, question in PREDEFINED_QUESTIONS.items():
            if st.checkbox(question, key=f"q_{key}_{st.session_state.reset_counter}"):
                selected_questions.append(question)
        
        st.markdown("---")
        st.markdown("**Β) Προσαρμοσμένες Ερωτήσεις** - Γράψε τις δικές σου ερωτήσεις (μία ανά γραμμή):")
        custom_questions_text = st.text_area(
            "Οι ερωτήσεις σου:",
            height=150,
            key=f"custom_q_{st.session_state.reset_counter}",
            placeholder="Παράδειγμα:\nΠώς επηρεάζει ο    # ============ QUESTIONS PROCESSING ============
    if generate_questions:
        if st.session_state.basic_report is None:
            st.error("⚠️ Πρέπει πρώτα να δημιουργήσεις τη Βασική Αναφορά!")
            st.info("👆 Πάτησε τοimport os
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

PREDEFINED_QUESTIONS = {
    "talents": "🌟 Ταλέντα: Ποια είναι τα φυσικά ταλέντα και οι δυνατότητές μου σύμφωνα με τον χάρτη;",
    "interests": "❤️ Ενδιαφέροντα: Σε ποιους τομείς ζωής ή δραστηριότητες θα αισθανθώ ικανοποίηση και εκπλήρωση;",
    "healing": "🌿 Θεραπεία: Τι χρειάζομαι για εσωτερική ισορροπία και ψυχική ανάπτυξη;",
    "challenges": "⚡ Αδυναμίες/Αποφυγή: Ποιες προκλήσεις με περιμένουν και τι πρέπει να προσέξω;",
    "careers": "💼 Επαγγελματικός Προσανατολισμός: Ποια 5-7 συγκεκριμένα επαγγέλματα ταιριάζουν στις δυνατότητές και τα ταλέντα μου; (π.χ. Ψυχολόγος, Αρχιτέκτονας, Δημοσιογράφος, κλπ.)",
    "avoid_careers": "🚫 Επαγγέλματα προς Αποφυγή: Ποια επαγγέλματα ή τομείς εργασίας δεν ταιριάζουν στη φύση μου και γιατί να τα αποφύγω; Να αναφερθούν συγκεκριμένα παραδείγματα.",
}

HOUSE_THEMES = {
    1: "εγώ & σώμα",
    2: "χρήματα & αξίες",
    3: "επικοινωνία & μάθηση",
    4: "σπίτι & οικογένεια",
    5: "έρωτας & παιδιά",
    6: "δουλειά & υγεία",
    7: "σχέσεις & γάμος",
    8: "βαθιά οικειότητα & κοινά χρήματα",
    9: "ταξίδια & ανώτερες σπουδές",
    10: "καριέρα & κοινωνική εικόνα",
    11: "φίλοι & όραμα",
    12: "ασυνείδητο & θεραπεία",
}


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
    
    return warnings


# ============ OPENAI FUNCTIONS (CACHED) ============
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


@st.cache_data(show_spinner=False)
def generate_houses_analysis_cached(payload_hash: str, payload: dict) -> str:
    return generate_houses_analysis_with_openai(payload)


def generate_houses_analysis_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."

    # Prepare house data for each house
    houses_data = []
    for house_num in range(1, 13):
        house_info = next((h for h in payload.get("houses", []) if h["house"] == house_num), None)
        if not house_info:
            continue
        
        # Get planets in this house
        planets_in_house = [
            {"planet": p["planet"], "sign": p["sign"]}
            for p in payload.get("planets_in_houses", [])
            if p["house"] == house_num and p["sign"]
        ]
        
        # Get ruler position
        ruler = house_info.get("ruler")
        ruler_gr = house_info.get("ruler_gr")
        ruler_planet_info = next(
            (p for p in payload.get("planets_in_houses", []) if p["planet"] == ruler),
            None
        )
        if ruler_planet_info:
            ruler_position = f"{ruler_gr} στον {ruler_planet_info['sign']} στον {ruler_planet_info['house']}ο οίκο"
        else:
            ruler_position = f"{ruler_gr} (θέση μη καταγεγραμμένη)"
        
        # Get major aspects affecting this house
        major_aspects = []
        for aspect in payload.get("aspects", []):
            p1, p2 = aspect["p1"], aspect["p2"]
            # Include if ruler or any planet in house is involved
            planets_to_check = [ruler] + [p["planet"] for p in planets_in_house]
            if p1 in planets_to_check or p2 in planets_to_check:
                major_aspects.append({
                    "from": aspect["p1"],
                    "to": aspect["p2"],
                    "type": aspect["aspect"],
                    "orb": 2  # Default orb
                })
        
        houses_data.append({
            "house_number": house_num,
            "house_theme": HOUSE_THEMES.get(house_num, ""),
            "house_sign": house_info["sign"],
            "house_ruler_planet": ruler,
            "house_ruler_position": ruler_position,
            "planets_in_house": planets_in_house,
            "major_aspects": major_aspects,
        })

    system_prompt = """MASTER PROMPT – Ερμηνεία Οίκων (1–12)

Ρόλος: Είσαι μια έμπειρη, σύγχρονη ψυχολογική αστρολόγος.
Η δουλειά σου είναι να εξηγείς έναν συγκεκριμένο οίκο του γενέθλιου χάρτη σε μία παράγραφο, ζεστά, πρακτικά και ενδυναμωτικά, χωρίς φόβο και μοιρολατρία.

Τι πρέπει να κάνεις:
1. Χρησιμοποίησε το house_theme και το house_number για να ξεκινήσεις με 1–2 προτάσεις που εξηγούν σε ποιο πεδίο της ζωής αναφέρεται ο οίκος.
2. Με βάση το house_sign και τον house_ruler_planet μαζί με το house_ruler_position, περιέγραψε πώς εκφράζεται η ενέργεια αυτού του οίκου.
3. Αν υπάρχουν planets_in_house, ενσωμάτωσε τους στο κείμενο: εξήγησε τι χρώμα δίνει κάθε πλανήτης στα θέματα του οίκου. Μην κάνεις λίστα· πες το σαν ιστορία.
4. Χρησιμοποίησε τις major_aspects για να δώσεις 2–4 συγκεκριμένα παραδείγματα για το πώς βιώνει το άτομο αυτόν τον οίκο στην πράξη.
   - ΜΗΝ γράφεις τεχνική γλώσσα του τύπου «τετράγωνο Άρη–Κρόνου». Μετέφρασε την ουσία της όψης σε απλή ψυχολογική/πρακτική γλώσσα.
   - Αρμονικές όψεις (trine, sextile) = φυσικές διευκολύνσεις, ταλέντα, υποστήριξη.
   - Δύσκολες όψεις (square, opposition) = προκλήσεις ή εσωτερικές συγκρούσεις που βοηθούν το άτομο να ωριμάσει.
5. Σύνδεσε πάντα ό,τι περιγράφεις με το πραγματικό θέμα του οίκου.
6. Κλείσε την παράγραφο με 1–2 προτάσεις θεραπευτικής/εξελικτικής κατεύθυνσης.

Στυλ κειμένου:
- Γράψε σε απλή, καθημερινή ελληνική, σαν να μιλάς σε φίλη που δεν ξέρει αστρολογία.
- Απόφυγε τεχνικούς όρους. Αν χρειαστεί, εξήγησε το ψυχολογικό νόημα.
- Η απάντηση πρέπει να είναι μία ενιαία παράγραφος, 5–8 προτάσεων, χωρίς τίτλους, bullets ή λίστες.
- Ύφος ζεστό, ενθαρρυντικό, με κατανόηση. Μην γράφεις τρομακτικά ή απόλυτες φράσεις.
- Στόχος: το άτομο να καταλάβει καλύτερα τον εαυτό του και να νιώσει ότι έχει επιλογές και δύναμη."""

    user_prompt = f"""Θα σου δώσω δεδομένα για ΟΛΟΥΣ τους 12 οίκους. Για κάθε οίκο, γράψε ΜΙΑ παράγραφο (5-8 προτάσεις) σύμφωνα με το MASTER PROMPT.

Δομή απάντησης:
ΟΙΚΟΣ 1
[η παράγραφός σου]

ΟΙΚΟΣ 2
[η παράγραφός σου]

... και ούτω καθεξής για όλους τους 12 οίκους.

Δεδομένα:
{json.dumps(houses_data, ensure_ascii=False, indent=2)}"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_custom_analysis_with_openai(payload: dict, questions: List[str], basic_report: str) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."

    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
    
    system_prompt = """Είσαι έμπειρη αστρολόγος.
Λαμβάνεις:
- Ένα JSON με γενέθλιο χάρτη (basic_info, houses, planets_in_houses, aspects)
- ΜΙΑ ΑΝΑΛΥΤΙΚΗ ΑΝΑΦΟΡΑ που έχει ήδη δημιουργηθεί για αυτό το άτομο
- Συγκεκριμένες ερωτήσεις από τον χρήστη

ΚΡΙΣΙΜΟ: Η ανάλυσή σου ΠΡΕΠΕΙ να στηρίζεται στην υπάρχουσα αναφορά. Διάβασέ την προσεκτικά και χρησιμοποίησέ την ως βάση.

ΟΔΗΓΙΕΣ:
- Απάντησε ΜΟΝΟ στις ερωτήσεις που σου δίνονται
- ΧΡΗΣΙΜΟΠΟΙΗΣΕ τα συμπεράσματα από την υπάρχουσα αναφορά
- Αναφέρσου σε συγκεκριμένα σημεία από την αναφορά (π.χ. "Όπως είδαμε στην ανάλυση...")
- Για την ερώτηση επαγγελμάτων: πρότεινε 5-7 ΣΥΓΚΕΚΡΙΜΕΝΑ επαγγέλματα (όχι γενικόλογα) με σύντομη αιτιολογία για το καθένα
- Γράψε σε απλή, ζεστή, ενδυναμωτική ελληνική γλώσσα
- Για κάθε ερώτηση, γράψε 2-4 παραγράφους με συγκεκριμένα παραδείγματα
- Όχι μοιρολατρικό ύφος - εστίασε σε δυνατότητες και εξέλιξη"""

    user_prompt = f"""ΥΠΑΡΧΟΥΣΑ ΑΝΑΛΥΤΙΚΗ ΑΝΑΦΟΡΑ ΓΙΑ ΤΟ ΑΤΟΜΟ:
{basic_report}

---

ΔΕΔΟΜΕΝΑ ΧΑΡΤΗ (για αναφορά):
{json.dumps(payload, ensure_ascii=False, indent=2)}

---

ΕΡΩΤΗΣΕΙΣ ΠΡΟΣ ΑΠΑΝΤΗΣΗ:
{questions_text}

Να απαντήσεις με βάση την υπάρχουσα αναφορά και τον χάρτη. Κάνε αναφορές σε συγκεκριμένα σημεία από την ανάλυση."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


# ============ PDF GENERATION ============
def create_pdf(payload: dict, basic_report: str, questions_report: Optional[str] = None, houses_report: Optional[str] = None) -> BytesIO:
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
    
    full_name = basic.get("full_name", "")
    gender = basic.get("gender", "")
    if full_name:
        story.append(Paragraph(f"Ονοματεπώνυμο: {full_name}", body_style))
    if gender:
        story.append(Paragraph(f"Φύλο: {gender}", body_style))
    
    story.append(Paragraph(f"Ζώδιο Ηλίου: {basic.get('sun_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ωροσκόπος: {basic.get('asc_sign_gr', 'N/A')}", body_style))
    story.append(Paragraph(f"Ζώδιο Σελήνης: {basic.get('moon_sign_gr', 'N/A')}", body_style))
    story.append(Spacer(1, 1*cm))

    # Basic Report
    story.append(Paragraph("Βασική Αναφορά (Ενότητες 0-3)", heading_style))
    for para in basic_report.split('\n\n'):
        if para.strip():
            safe_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_para, body_style))
            story.append(Spacer(1, 0.3*cm))
    
    # Questions Report (if exists)
    if questions_report:
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("Απαντήσεις σε Ερωτήσεις", heading_style))
        for para in questions_report.split('\n\n'):
            if para.strip():
                safe_para = para.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                story.append(Paragraph(safe_para, body_style))
                story.append(Spacer(1, 0.3*cm))
    
    # Houses Report (if exists)
    if houses_report:
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("Ψυχολογική Ανάλυση Οίκων (1-12)", heading_style))
        for para in houses_report.split('\n\n'):
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
    - ✅ **2 κουμπιά**: Βασική Αναφορά & Εξειδικευμένες Ερωτήσεις (με βάση την αναφορά)
    """)

    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    if "basic_report" not in st.session_state:
        st.session_state.basic_report = None
    if "payload" not in st.session_state:
        st.session_state.payload = None
    if "questions_report" not in st.session_state:
        st.session_state.questions_report = None
    if "houses_report" not in st.session_state:
        st.session_state.houses_report = None

    # ============ SECTION -1: NAME & GENDER ============
    st.header("📝 Στοιχεία Ατόμου")
    col_name, col_gender = st.columns([2, 1])
    with col_name:
        full_name = st.text_input(
            "Ονοματεπώνυμο",
            key=f"full_name_{st.session_state.reset_counter}",
            placeholder="π.χ. Μαρία Παπαδοπούλου"
        )
    with col_gender:
        gender = st.radio(
            "Φύλο",
            options=["Άνδρας", "Γυναίκα"],
            key=f"gender_{st.session_state.reset_counter}",
            horizontal=True
        )

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
                label_text = f"**{pair_index}.** {gr1} – {gr2}"
                key = f"aspect_{en1}_{en2}_{st.session_state.reset_counter}"
                
                choice = st.selectbox(
                    label_text, 
                    aspect_labels, 
                    key=key
                )
                aspects_selected_ui[(en1, en2)] = choice
                pair_index += 1

    # ============ ACTION BUTTONS ============
    st.markdown("---")
    st.subheader("📊 Δημιουργία Αναφοράς")
    
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    
    with col_btn1:
        generate_basic = st.button("🔍 Βασική Αναφορά (Ενότητες 0–3)", type="primary", use_container_width=True)
    
    with col_btn2:
        generate_questions = st.button("💎 Ερωτήσεις", type="secondary", use_container_width=True)
    
    with col_btn3:
        generate_houses = st.button("🏠 Ανάλυση Οίκων (1-12)", type="secondary", use_container_width=True)

    # ============ BASIC REPORT PROCESSING ============
    if generate_basic:
        if sun_sign_gr == "---" or asc_sign_gr == "---" or moon_sign_gr == "---":
            st.error("⚠️ Παρακαλώ συμπλήρωσε Ζώδιο Ηλίου, Ωροσκόπο και Ζώδιο Σελήνης!")
            return

        basic_info = {
            "full_name": full_name.strip(),
            "gender": gender,
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
                st.session_state.basic_report = report_text
                st.session_state.payload = payload
            except Exception as e:
                report_text = f"Σφάλμα: {e}"
        
        st.markdown("### 📜 Αναφορά Γενέθλιου Χάρτη (Ενότητες 0–3)")
        st.write(report_text)
        st.markdown("---")
        
        st.success("✅ Η αναφορά ολοκληρώθηκε!")

    # ============ MEGA PDF DOWNLOAD BUTTON ============
    if st.session_state.basic_report:
        st.markdown("---")
        st.subheader("📄 Λήψη Πλήρους Αναφοράς")
        
        sections_included = ["✅ Βασική Αναφορά"]
        if st.session_state.questions_report:
            sections_included.append("✅ Ερωτήσεις")
        if st.session_state.houses_report:
            sections_included.append("✅ Ανάλυση Οίκων")
        
        st.markdown(f"**Το PDF θα περιλαμβάνει:** {' | '.join(sections_included)}")
        
        pdf_buffer = create_pdf(
            st.session_state.payload,
            st.session_state.basic_report,
            st.session_state.questions_report,
            st.session_state.houses_report
        )
        st.download_button(
            "📥 Κατέβασμα Πλήρους Αναφοράς (PDF)", 
            data=pdf_buffer,
            file_name=f"astro_full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # ============ QUESTIONS PROCESSING ============
    if generate_questions:
        if st.session_state.basic_report is None:
            st.error("⚠️ Πρέπει πρώτα να δημιουργήσεις τη Βασική Αναφορά!")
            st.info("👆 Πάτησε το κουμπί 'Δημιουργία Βασικής Αναφοράς' πρώτα.")
            return
        
        st.subheader("💎 Επιλογή Ερωτήσεων")
        
        st.markdown("**Α) Προκαθορισμένες Ερωτήσεις** - Διάλεξε όσες σε ενδιαφέρουν:")
        selected_questions = []
        for key, question in PREDEFINED_QUESTIONS.items():
            if st.checkbox(question, key=f"q_{key}_{st.session_state.reset_counter}"):
                selected_questions.append(question)
        
        st.markdown("---")
        st.markdown("**Β) Προσαρμοσμένες Ερωτήσεις** - Γράψε τις δικές σου ερωτήσεις (μία ανά γραμμή):")
        custom_questions_text = st.text_area(
            "Οι δικές σου ερωτήσεις:",
            height=150,
            key=f"custom_q_{st.session_state.reset_counter}",
            placeholder="Παράδειγμα:\nΠώς επηρεάζει ο Κρόνος την καριέρα μου;\nΤι σημαίνει ο Άρης στον 7ο οίκο για τις σχέσεις μου;\nΠοια είναι η σχέση μου με το χρήμα;"
        )
        
        # Parse custom questions
        if custom_questions_text.strip():
            custom_lines = [line.strip() for line in custom_questions_text.strip().split('\n') if line.strip()]
            selected_questions.extend(custom_lines)
        
        if not selected_questions:
            st.info("💡 Δεν επιλέχθηκε καμία ερώτηση. Επίλεξε από τις προκαθορισμένες ή γράψε δικές σου.")
            return
        
        st.markdown("---")
        st.markdown(f"**Σύνολο Ερωτήσεων: {len(selected_questions)}**")
        for i, q in enumerate(selected_questions, 1):
            st.markdown(f"{i}. {q}")
        
        questions_hash = hashlib.sha256(
            json.dumps(selected_questions, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        report_hash = hashlib.sha256(st.session_state.basic_report.encode()).hexdigest()
        payload_hash = compute_payload_hash(st.session_state.payload)
        
        st.markdown("---")
        st.subheader("🤖 Εξειδικευμένη Ανάλυση")
        with st.spinner("⏳ Αναλύω με βάση την αναφορά σου..."):
            try:
                analysis_text = generate_custom_analysis_cached(
                    payload_hash, 
                    questions_hash, 
                    report_hash,
                    st.session_state.payload, 
                    selected_questions,
                    st.session_state.basic_report
                )
            except Exception as e:
                analysis_text = f"Σφάλμα: {e}"
        
        st.markdown("### 💫 Απαντήσεις")
        st.write(analysis_text)
        
        # Save to session state
        st.session_state.questions_report = analysis_text
        
        st.success("✅ Η ανάλυση ολοκληρώθηκε!")

    # ============ HOUSES ANALYSIS PROCESSING ============
    if generate_houses:
        if st.session_state.basic_report is None:
            st.error("⚠️ Πρέπει πρώτα να δημιουργήσεις τη Βασική Αναφορά!")
            st.info("👆 Πάτησε το κουμπί 'Βασική Αναφορά' πρώτα.")
            return
        
        payload_hash = compute_payload_hash(st.session_state.payload)
        
        st.subheader("🏠 Ψυχολογική Ανάλυση Οίκων (1-12)")
        st.markdown("Εξειδικευμένη ανάλυση κάθε οίκου με βάση το MASTER PROMPT.")
        
        with st.spinner("⏳ Δημιουργώ εις βάθος ανάλυση για κάθε οίκο..."):
            try:
                houses_text = generate_houses_analysis_cached(payload_hash, st.session_state.payload)
            except Exception as e:
                houses_text = f"Σφάλμα: {e}"
        
        st.markdown("### 🏛️ Ανάλυση Οίκων")
        st.write(houses_text)
        
        # Save to session state
        st.session_state.houses_report = houses_text
        
        st.success("✅ Η ανάλυση των οίκων ολοκληρώθηκε!")

    st.markdown("---")
    if st.button("🔄 Επανεκκίνηση (μηδενισμός όλων)"):
        st.session_state.reset_counter += 1
        st.session_state.basic_report = None
        st.session_state.payload = None
        st.session_state.questions_report = None
        st.session_state.houses_report = None
        st.rerun()
    
    st.caption("💡 **Tip:** Το caching εξοικονομεί χρόνο & κόστος στις επαναλήψεις.")


if __name__ == "__main__":
    main()