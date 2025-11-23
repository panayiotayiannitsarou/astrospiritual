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

TTFont = ttfonts.TTFont

# Ζώδια: Ελληνικά -> Αγγλικά
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


def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_basic_report_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return (
            "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον.\n"
            "Ρύθμισέ το για να μπορεί να κληθεί αυτόματα το ChatGPT."
        )

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
    – του ζωδίου της ακμής και
    – του κυβερνήτη του ζωδίου (σε ποιον οίκο βρίσκεται και τι σημαίνει αυτό).

3. ΕΝΟΤΗΤΑ 3 – Όψεις ανάμεσα σε πλανήτες (δομή με αριθμούς)
Γράψε τις όψεις οργανωμένα σε υποενότητες, με αριθμημένες γραμμές όπως στο παράδειγμα:

3.1 Όψεις Ήλιου
- Συμπερίλαβε μόνο τις όψεις που έχουν τον Ήλιο (Sun) ΚΑΙ υπάρχουν στη λίστα "aspects" του JSON.
- Γράψε τες αριθμημένα, με μορφή:
  1. Ήλιος – Σελήνη
  2. Ήλιος – Ερμής
  3. Ήλιος – Αφροδίτη
  κ.ο.κ., αλλά ΜΟΝΟ για τα ζευγάρια που πραγματικά εμφανίζονται στις "aspects".
- Κάτω από κάθε γραμμή (κάθε ζευγάρι) γράψε μια μικρή παράγραφο 3–4 προτάσεων που να εξηγεί:
  • τη δυναμική ανάμεσα στους δύο πλανήτες,
  • τα βασικά ψυχολογικά θέματα που ανοίγει η όψη,
  • πώς μπορεί το άτομο να την αξιοποιήσει πιο συνειδητά.

3.2 Όψεις Σελήνης
- Αντίστοιχα, βάλε εδώ όλες τις όψεις που έχουν τη Σελήνη (Moon) και υπάρχουν στο JSON.
- Γράψε τες αριθμημένα:
  1. Σελήνη – Ερμής
  2. Σελήνη – Αφροδίτη
  3. Σελήνη – Άρης
  κ.ο.κ., μόνο για τα ζευγάρια που όντως υπάρχουν στη λίστα "aspects".
- Κάτω από κάθε γραμμή, μια παράγραφος 3–4 προτάσεων, με έμφαση στο συναισθηματικό βίωμα, τις ανάγκες και την ασφάλεια.

3.3 Όψεις υπόλοιπων πλανητών
- Εδώ βάζεις, με την ίδια λογική, τις όψεις των υπόλοιπων πλανητών (Ερμή, Αφροδίτης, Άρη, Δία, Κρόνου, Ουρανού, Ποσειδώνα, Πλούτωνα κτλ.).
- Ομαδοποίησέ τες ανά πλανήτη, π.χ.:
  • Όψεις Ερμή
    1. Ερμής – Αφροδίτη
    2. Ερμής – Άρης
  • Όψεις Αφροδίτης
    1. Αφροδίτη – Άρης
    2. Αφροδίτη – Δίας
- Αν κάποιος πλανήτης δεν έχει καμία όψη στο JSON, μπορείς να παραλείψεις την υποενότητά του.
- Σε κάθε ζευγάρι κράτα την ίδια λογική: μια σύντομη αλλά ουσιαστική παράγραφος 2–4 προτάσεων.
- ΜΗΝ εφευρίσκεις επιπλέον όψεις· χρησιμοποίησε μόνο όσες υπάρχουν στη λίστα "aspects".

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


def generate_section4_report_with_openai(payload: dict) -> str:
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."

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


def generate_section5_aspects_with_openai(payload: dict) -> str:
    """
    ΜΟΝΟ Ενότητα 5 – Όψεις (σε υποενότητες 5Α, 5Β, 5Γ).
    Χρησιμοποιεί ΟΛΟ το context (basic_info, houses, planets_in_houses),
    αλλά αναλύει ΜΟΝΟ τις όψεις που υπάρχουν στη λίστα "aspects".
    """
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη:

- basic_info: ζώδιο Ήλιου, Ωροσκόπου, Σελήνης (στα ελληνικά και αγγλικά),
- houses: για κάθε οίκο 1–12, το ζώδιο της ακμής, ο κυβερνήτης του ζωδίου και (αν υπάρχει) ο οίκος στον οποίο βρίσκεται ο κυβερνήτης,
- planets_in_houses: σε ποιον οίκο βρίσκεται κάθε πλανήτης/σημείο,
- aspects: λίστα από όψεις ανάμεσα σε δυο πλανήτες/σημεία.

Χρησιμοποίησε τα στοιχεία των οίκων και των πλανητών σε οίκους ΜΟΝΟ ως πλαίσιο, για να καταλαβαίνεις καλύτερα τα θέματα ζωής που ενεργοποιεί κάθε όψη.
ΔΕΝ θα γράψεις ανάλυση οίκων ή ενότητα για πλανήτες σε οίκους.
Θα γράψεις ΜΟΝΟ την ΕΝΟΤΗΤΑ 5 – Όψεις, χωρισμένη σε υποενότητες.

5. ΕΝΟΤΗΤΑ 5 – Όψεις (σε υποενότητες)

5Α. Βασικές ψυχολογικές όψεις
- Εδώ θα βάλεις όψεις που περιλαμβάνουν τον Ήλιο (Sun), τη Σελήνη (Moon), τον Ωροσκόπο (AC) ή τον κυβερνήτη Ωροσκόπου.
- Ο κυβερνήτης του Ωροσκόπου προκύπτει από το ζώδιο του Ωροσκόπου (π.χ. Κριός→Άρης, Ταύρος→Αφροδίτη, Τοξότης→Δίας, Υδροχόος→Ουρανός κ.λπ.).
- Για κάθε τέτοια όψη γράψε ΜΙΑ ξεχωριστή, μικρή παράγραφο 3–4 προτάσεων:
  πώς επηρεάζει τον χαρακτήρα, τη βασική ψυχολογία, τον τρόπο που νιώθει και εκφράζεται το άτομο.

5Β. Θεραπευτικές / καρμικές όψεις
- Εδώ θα βάλεις όψεις που περιλαμβάνουν Χείρωνα (Chiron), Βόρειο Δεσμό (North Node), Κρόνο (Saturn) ή Πλούτωνα (Pluto),
  καθώς και όψεις αυτών με AC ή MC.
- Για κάθε τέτοια όψη γράψε ΜΙΑ ξεχωριστή παράγραφο 3–5 προτάσεων:
  μίλησε για πληγές, μοτίβα, φόβους ή βάρη, αλλά και για το μάθημα, την πιθανή θεραπεία και την εξέλιξη που προσφέρει η όψη.

5Γ. Λοιπές όψεις
- Εδώ θα βάλεις όλες τις υπόλοιπες όψεις που απομένουν και δεν έχουν ήδη αναλυθεί στις προηγούμενες υποενότητες.
- Για κάθε μία γράψε ΜΙΑ ξεχωριστή μικρή παράγραφο 2–4 προτάσεων:
  πώς συνεργάζονται οι δυο πλανήτες, σε ποια θέματα ζωής, τι ταλέντο, ένταση ή δυναμική δημιουργείται.

ΣΗΜΑΝΤΙΚΟ:
- Η λίστα 'aspects' στο JSON περιέχει ΜΟΝΟ τις όψεις που θέλω να αναλύσεις σε αυτή την αναφορά.
  Μην υποθέτεις άλλες όψεις εκτός από αυτές.
- Γράψε ξεχωριστή παράγραφο για ΚΑΘΕ όψη που υπάρχει στο JSON, χωρίς να τις συγχωνεύσεις.
- Αν μια όψη θα μπορούσε να ανήκει σε περισσότερες από μία υποενότητες (π.χ. Ήλιος–Κρόνος),
  διάλεξε την υποενότητα όπου η όψη έχει περισσότερο ψυχολογικό/θεραπευτικό βάρος (συνήθως 5Β).
- Αν οι όψεις είναι πάρα πολλές (π.χ. πάνω από 10),
  δώσε πιο αναλυτικό βάθος (3–5 προτάσεις) στις όψεις με Ήλιο, Σελήνη, Ωροσκόπο, Χείρωνα, Βόρειο Δεσμό, Κρόνο ή Πλούτωνα
  και για τις υπόλοιπες αρκούν 2–3 καθαρές προτάσεις.

ΥΦΟΣ:
- Γράψε σε απλή, καθαρή, σύγχρονη ελληνική γλώσσα.
- Να είναι ζεστό, ενδυναμωτικό, με σεβασμό, χωρίς μοιρολατρία.
- Μη χρησιμοποιείς πολλή τεχνική ορολογία χωρίς εξήγηση.
- Μη μιλάς για "καλό/κακό χάρτη". Μίλα για δυνατότητες, προκλήσεις και εξέλιξη.
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
    """
    Αναλύει ΜΙΑ ΜΟΝΟ όψη, αλλά στέλνει ολόκληρο το χάρτη (houses, planets_in_houses)
    για να έχει πλήρες context.
    """
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY."

    system_prompt = """Είσαι έμπειρη αστρολόγος.
Θα λάβεις ένα ΠΛΗΡΕΣ JSON γενέθλιου χάρτη (basic_info, houses, planets_in_houses, aspects).
Αλλά θα σου δώσω και μία ΣΥΓΚΕΚΡΙΜΕΝΗ όψη προς ανάλυση.

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
    """
    Καλεί το OpenAI για ΚΑΘΕ όψη ξεχωριστά, με πλήρες context.
    Επιστρέφει ενωμένο κείμενο με όλες τις ερμηνείες.
    """
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
    for idx, aspect_obj in enumerate(aspects_list):
        status_text.text(f"Αναλύω όψη {idx+1}/{total}: {aspect_obj['p1_gr']} - {aspect_obj['p2_gr']}")
        
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
    """
    Παράγει ΠΛΗΡΗ αναφορά: Ενότητες 0-3, 4, 5 σε ένα κείμενο.
    Καλεί το OpenAI 3 φορές και ενώνει τα αποτελέσματα.
    """
    client = get_openai_client()
    if client is None:
        return "⚠️ Δεν βρέθηκε OPENAI_API_KEY στο περιβάλλον."
    
    report_parts = []
    
    # Μέρος 1: Βασική αναφορά (0-3)
    try:
        basic = generate_basic_report_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Α: ΒΑΣΙΚΗ ΑΝΑΦΟΡΑ (Ενότητες 0-3)")
        report_parts.append("=" * 80)
        report_parts.append(basic)
        report_parts.append("\n\n")
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στη βασική αναφορά: {e}\n\n")
    
    # Μέρος 2: Ταλέντα (4)
    try:
        talents = generate_section4_report_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Β: ΤΑΛΕΝΤΑ & ΕΣΩΤΕΡΙΚΗ ΠΟΡΕΙΑ (Ενότητα 4)")
        report_parts.append("=" * 80)
        report_parts.append(talents)
        report_parts.append("\n\n")
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στην ενότητα 4: {e}\n\n")
    
    # Μέρος 3: Όψεις (5)
    try:
        aspects = generate_section5_aspects_with_openai(payload)
        report_parts.append("=" * 80)
        report_parts.append("ΜΕΡΟΣ Γ: ΑΝΑΛΥΤΙΚΕΣ ΟΨΕΙΣ (Ενότητα 5)")
        report_parts.append("=" * 80)
        report_parts.append(aspects)
    except Exception as e:
        report_parts.append(f"⚠️ Σφάλμα στην ενότητα 5: {e}\n\n")
    
    return "\n".join(report_parts)


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


def main():
    st.set_page_config(page_title="Γενέθλιος Χάρτης – Beta", layout="wide")
    st.title("🪷 Προσωπική Έκθεση Γενέθλιου Χάρτη – Beta")

    st.markdown("Αυτό το εργαλείο σε βοηθά να διαβάζεις τον χάρτη από το astro.com "
                "και να φτιάχνεις δομημένα δεδομένα για μια αναλυτική έκθεση με ChatGPT.")

    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0

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

    st.header("1. Ενότητα 1 – Ακμές οίκων (ζώδιο σε κάθε οίκο)")
    st.markdown("Διάβασε από τον χάρτη σου σε ποιο ζώδιο ξεκινά κάθε οίκος (1–12) και διάλεξέ το.")

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

    st.header("2. Ενότητα 2 – Πλανήτες σε οίκους")
    st.markdown("Για κάθε οίκο (1–12), διάλεξε ποιοι πλανήτες βρίσκονται μέσα σε αυτόν τον οίκο.")

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

            available_planets = ["Κανένας"] + [p for p in planet_names_gr if p not in already_selected]
            selected_planets_gr = st.multiselect(f"Πλανήτες στον Οίκο {i}", available_planets,
                key=f"house_planets_{i}_{st.session_state.reset_counter}")
        house_planets_map[i] = selected_planets_gr

    planet_house_map = {}
    for house_num, planets_gr_list in house_planets_map.items():
        if "Κανένας" in planets_gr_list or len(planets_gr_list) == 0:
            continue
        for gr_name in planets_gr_list:
            if gr_name == "Κανένας":
                continue
            en_name = next(en for (gr, en) in PLANETS if gr == gr_name)
            planet_house_map[en_name] = house_num

    # 🔹 Βελτιωμένη Ενότητα 3 με αριθμημένες όψεις
    st.header("3. Ενότητα 3 – Όψεις ανάμεσα σε πλανήτες")
    st.markdown(
        """
Για κάθε ζευγάρι πλανητών, αν υπάρχει σημαντική όψη, διάλεξε τη μορφή της από το dropdown.

- Οι όψεις είναι ομαδοποιημένες ανά πλανήτη (π.χ. **Όψεις Ήλιος**, **Όψεις Σελήνη** κτλ.).
- Κάτω από κάθε ομάδα θα δεις αριθμημένες γραμμές, όπως:
  - `1. Ήλιος – Σελήνη`
  - `2. Ήλιος – Ερμής`
- Δίπλα σε κάθε ζευγάρι διάλεξε την όψη (σύνοδο, τρίγωνο κ.λπ.) ή άφησε **Καμία** αν δεν υπάρχει όψη.
        """
    )

    aspect_labels = [opt[0] for opt in ASPECT_OPTIONS]
    label_to_code = {opt[0]: opt[1] for opt in ASPECT_OPTIONS}

    aspects_selected_ui = {}
    for i, (gr1, en1) in enumerate(PLANETS):
        if gr1 in ("AC", "MC"):
            continue
        st.markdown(f"#### Όψεις {gr1}")
        pair_index = 1  # μετρητής για 1., 2., 3. κτλ μέσα σε κάθε ομάδα

        for j in range(i + 1, len(PLANETS)):
            gr2, en2 = PLANETS[j]
            # Αριθμημένη ετικέτα, π.χ. "1. Ήλιος – Σελήνη"
            label_text = f"{pair_index}. {gr1} – {gr2}"
            key = f"aspect_{en1}_{en2}_{st.session_state.reset_counter}"
            choice = st.selectbox(label_text, aspect_labels, key=key)
            aspects_selected_ui[(en1, en2)] = choice
            pair_index += 1

    st.markdown("---")
    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
    with col_b1:
        basic_button = st.button("📝 Βασική αναφορά (Ενότητες 0–3)")
    with col_b2:
        talents_button = st.button("🌟 Ενότητα 4 – Ταλέντα & Θεραπευτική Πορεία")
    with col_b3:
        aspects_button = st.button("🔮 Ενότητα 5 – Όψεις (αναλυτικά)")
    with col_b4:
        per_aspect_button = st.button("🔍 Ερμηνεία Κάθε Όψης Ξεχωριστά")
    with col_b5:
        full_button = st.button("📕 Πλήρης Αναφορά (Όλες οι Ενότητες)")

    if basic_button or talents_button or aspects_button or per_aspect_button or full_button:
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
            planets_in_houses.append({"planet": en_name, "planet_gr": gr_name, "house": house_num})

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

        st.subheader("📋 JSON δεδομένων χάρτη")
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

        if basic_button:
            st.subheader("🤖 Βασική αναφορά με OpenAI (Ενότητες 0–3)")
            with st.spinner("Καλώ το μοντέλο..."):
                try:
                    report_text = generate_basic_report_with_openai(payload)
                except Exception as e:
                    report_text = f"Σφάλμα: {e}"
            st.markdown("### 📜 Αναφορά (Ενότητες 0–3)")
            st.write(report_text)
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button("📄 Λήψη Βασικής Αναφοράς σε PDF", data=pdf_buffer,
                file_name=f"basic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf")

        if talents_button:
            st.subheader("🤖 Αναφορά Ενότητας 4 με OpenAI")
            with st.spinner("Καλώ το μοντέλο..."):
                try:
                    report_text = generate_section4_report_with_openai(payload)
                except Exception as e:
                    report_text = f"Σφάλμα: {e}"
            st.markdown("### 📜 Ενότητα 4 – Ταλέντα")
            st.write(report_text)
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button("📄 Λήψη Ενότητας 4 σε PDF", data=pdf_buffer,
                file_name=f"section4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf")

        if aspects_button:
            st.subheader("🤖 Αναφορά Ενότητας 5 – Όψεις με OpenAI")
            with st.spinner("Καλώ το μοντέλο..."):
                try:
                    report_text = generate_section5_aspects_with_openai(payload)
                except Exception as e:
                    report_text = f"Σφάλμα: {e}"
            st.markdown("### 📜 Ενότητα 5 – Όψεις")
            st.write(report_text)
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button("📄 Λήψη Ενότητας 5 σε PDF", data=pdf_buffer,
                file_name=f"section5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf")

        if per_aspect_button:
            st.subheader("🔍 Ερμηνεία Κάθε Όψης Ξεχωριστά (με πλήρες context)")
            st.markdown("**Κάθε όψη θα αναλυθεί μεμονωμένα με βάση ολόκληρο το χάρτη.**")
            
            if not aspects:
                st.warning("⚠️ Δεν υπάρχουν όψεις προς ανάλυση.")
            else:
                with st.spinner(f"Αναλύω {len(aspects)} όψεις... Αυτό μπορεί να πάρει λίγο χρόνο."):
                    try:
                        report_text = generate_all_aspects_separately(payload)
                    except Exception as e:
                        report_text = f"Σφάλμα: {e}"
                
                st.markdown("### 📜 Αναλυτική Ερμηνεία Όλων των Όψεων")
                st.write(report_text)
                pdf_buffer = create_pdf(payload, report_text)
                st.download_button("📄 Λήψη Αναλυτικών Όψεων σε PDF", data=pdf_buffer,
                    file_name=f"per_aspect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf")

        if full_button:
            st.subheader("🤖 Πλήρης Αναφορά με OpenAI (Όλες οι Ενότητες)")
            with st.spinner("Καλώ το μοντέλο 3 φορές για ολοκληρωμένη αναφορά... Μπορεί να πάρει 1-2 λεπτά."):
                try:
                    report_text = generate_full_report_with_openai(payload)
                except Exception as e:
                    report_text = f"Σφάλμα: {e}"
            st.markdown("### 📜 Πλήρης Αναφορά Γενέθλιου Χάρτη")
            st.write(report_text)
            st.markdown("---")
            pdf_buffer = create_pdf(payload, report_text)
            st.download_button("📄 Λήψη Πλήρους Αναφοράς σε PDF", data=pdf_buffer,
                file_name=f"full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf")
            st.success("✅ Πλήρης αναφορά ολοκληρώθηκε! Μπορείς να την κατεβάσεις ως PDF.")

    st.markdown("---")
    if st.button("🔄 Επανεκκίνηση (μηδενισμός όλων των δεδομένων)"):
        st.session_state.reset_counter += 1
        st.rerun()


if __name__ == "__main__":
    main()
