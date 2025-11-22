
import os
import json
import streamlit as st
from openai import OpenAI

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
    ("Χείρωνας", "Chiron"),
    ("Βόρειος Δεσμός", "North Node"),
]

# Όψεις: label για UI -> κωδικός για JSON
ASPECT_OPTIONS = [
    ("Καμία", None),
    ("Σύνοδος (0°)", "conjunction"),
    ("Αντίθεση (180°)", "opposition"),
    ("Τρίγωνο (120°)", "trine"),
    ("Τετράγωνο (90°)", "square"),
    ("Εξάγωνο (60°)", "sextile"),
]


def get_openai_client():
    """Φτιάχνει OpenAI client αν υπάρχει API key."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_report_with_openai(payload: dict) -> str:
    """
    Καλεί το OpenAI Chat Completions API και ζητά να γραφτεί η αναφορά
    με βάση τις 3 ενότητες που έχουμε σχεδιάσει.
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
        "Λαμβάνεις ως είσοδο ένα JSON με δομή γενέθλιου χάρτη: basic_info, houses, "
        "planets_in_houses και aspects.\n"
        "Θέλω να γράφεις ΠΑΝΤΑ σε καλή, καθαρή ελληνική γλώσσα.\n\n"
        "Να ακολουθείς αυτή τη δομή αναφοράς:\n"
        "0. Μικρό κουτάκι με βασικά στοιχεία (Ήλιος, Ωροσκόπος, Σελήνη).\n"
        "1. ΕΝΟΤΗΤΑ 1 – Οι ακμές των οίκων: για κάθε οίκο 1–12 μια σύντομη παράγραφο "
        "με θέμα οίκου + χρώμα ζωδίου ακμής.\n"
        "2. ΕΝΟΤΗΤΑ 2 – Πλανήτες & κυβερνήτες σε οίκους: για κάθε οίκο, αν έχει πλανήτες "
        "γράψε ανάλυση. Αν δεν έχει, εξήγησε τον οίκο μέσω του ζωδίου της ακμής και του "
        "κυβερνήτη του ζωδίου (πλανήτης και οίκος στον οποίο βρίσκεται).\n"
        "3. ΕΝΟΤΗΤΑ 3 – Όψεις: για κάθε όψη στο JSON, γράψε μια παράγραφο που εξηγεί "
        "τη δυναμική ανάμεσα στους δύο πλανήτες (όψεις που ΔΕΝ υπάρχουν στο JSON, αγνόησέ τες).\n\n"
        "Η γλώσσα να είναι ζεστή αλλά όχι υπερβολικά 'ποιητική'. Να είναι σαφής, "
        "παιδαγωγική και ενδυναμωτική."
    )

    user_prompt = (
        "Παρακάτω είναι τα δεδομένα του χάρτη σε JSON. "
        "Να γράψεις την Προσωπική Έκθεση Γενέθλιου Χάρτη στις 3 ενότητες όπως "
        "περιγράφονται στο system prompt.\n\n"
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


# ---------- UI STREAMLIT ----------

def main():
    st.set_page_config(page_title="Γενέθλιος Χάρτης – Beta", layout="wide")
    st.title("🪷 Προσωπική Έκθεση Γενέθλιου Χάρτη – Beta")

    st.markdown(
        "Αυτό το εργαλείο σε βοηθά να διαβάζεις τον χάρτη από το astro.com "
        "και να φτιάχνεις δομημένα δεδομένα για μια αναλυτική έκθεση με ChatGPT."
    )

    # ----- ΒΑΣΙΚΑ ΣΤΟΙΧΕΙΑ ΧΑΡΤΗ -----
    st.header("0. Βασικά στοιχεία χάρτη")

    col1, col2, col3 = st.columns(3)
    with col1:
        birth_date = st.text_input("Ημερομηνία γέννησης", placeholder="π.χ. 30/03/1995")
        birth_time = st.text_input("Ώρα γέννησης", placeholder="π.χ. 03:00")
    with col2:
        birth_place = st.text_input("Τόπος γέννησης", placeholder="π.χ. Βόλος, Ελλάδα")
    with col3:
        sun_sign_gr = st.selectbox("Ζώδιο Ήλιου", SIGNS_GR_LIST, index=SIGNS_GR_LIST.index("Υδροχόος"))
        asc_sign_gr = st.selectbox("Ωροσκόπος", SIGNS_GR_LIST, index=SIGNS_GR_LIST.index("Τοξότης"))
        moon_sign_gr = st.selectbox("Ζώδιο Σελήνης", SIGNS_GR_LIST, index=SIGNS_GR_LIST.index("Παρθένος"))

    # ----- ΕΝΟΤΗΤΑ 1: ΟΙΚΟΙ -----
    st.header("1. Ενότητα 1 – Ακμές οίκων (ζώδιο σε κάθε οίκο)")

    st.markdown("Διάβασε από τον χάρτη σου σε ποιο ζώδιο ξεκινά κάθε οίκος (1–12) και διάλεξέ το.")

    houses_signs_gr = {}
    cols = st.columns(4)
    for i in range(1, 13):
        col = cols[(i - 1) % 4]
        with col:
            sign = st.selectbox(
                f"Οίκος {i}",
                SIGNS_GR_LIST,
                key=f"house_{i}",
            )
        houses_signs_gr[i] = sign

    # ----- ΕΝΟΤΗΤΑ 2: ΠΛΑΝΗΤΕΣ ΣΕ ΟΙΚΟΥΣ -----
    st.header("2. Ενότητα 2 – Πλανήτες σε οίκους")

    st.markdown(
        "Για κάθε πλανήτη, επέλεξε σε ποιον οίκο βρίσκεται (ή 'Κανένας' αν δεν θες να τον χρησιμοποιήσεις)."
    )

    planet_house_map = {}
    house_choices = ["Κανένας"] + [str(i) for i in range(1, 13)]

    cols_plan = st.columns(3)
    for idx, (gr_name, en_name) in enumerate(PLANETS):
        col = cols_plan[idx % 3]
        with col:
            selection = st.selectbox(
                f"{gr_name} – Οίκος",
                house_choices,
                key=f"planet_{en_name}",
            )
        if selection != "Κανένας":
            planet_house_map[en_name] = int(selection)

    # ----- ΕΝΟΤΗΤΑ 3: ΟΨΕΙΣ -----
    st.header("3. Ενότητα 3 – Όψεις ανάμεσα σε πλανήτες")

    st.markdown(
        "Για κάθε ζευγάρι πλανητών, αν υπάρχει σημαντική όψη, διάλεξε τη μορφή της. "
        "Αν δεν υπάρχει ή δεν θες να την ερμηνεύσεις, άφησέ το 'Καμία'."
    )

    aspect_labels = [opt[0] for opt in ASPECT_OPTIONS]
    label_to_code = {opt[0]: opt[1] for opt in ASPECT_OPTIONS}

    # Widgets για όψεις: για κάθε μοναδικό ζευγάρι (p1, p2) με i < j
    aspects_selected_ui = {}
    for i, (gr1, en1) in enumerate(PLANETS):
        st.markdown(f"#### Όψεις {gr1}")
        for j in range(i + 1, len(PLANETS)):
            gr2, en2 = PLANETS[j]
            key = f"aspect_{en1}_{en2}"
            choice = st.selectbox(
                f"{gr1} – {gr2}",
                aspect_labels,
                key=key,
            )
            aspects_selected_ui[(en1, en2)] = choice

    # ----- ΚΟΥΜΠΙ ΔΗΜΙΟΥΡΓΙΑΣ ΑΝΑΦΟΡΑΣ -----
    st.markdown("---")
    generate_button = st.button("📝 Δημιουργία αναφοράς")

    if generate_button:
        # Φτιάχνουμε το payload (JSON) για ChatGPT
        basic_info = {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": birth_place,
            "sun_sign_gr": sun_sign_gr,
            "sun_sign": SIGNS_GR_TO_EN[sun_sign_gr],
            "asc_sign_gr": asc_sign_gr,
            "asc_sign": SIGNS_GR_TO_EN[asc_sign_gr],
            "moon_sign_gr": moon_sign_gr,
            "moon_sign": SIGNS_GR_TO_EN[moon_sign_gr],
        }

        houses = []
        for house_num, sign_gr in houses_signs_gr.items():
            houses.append(
                {
                    "house": house_num,
                    "sign_gr": sign_gr,
                    "sign": SIGNS_GR_TO_EN[sign_gr],
                }
            )

        planets_in_houses = []
        for en_name, house_num in planet_house_map.items():
            # Βρες το ελληνικό όνομα από τη λίστα PLANETS
            gr_name = next(gr for gr, en in PLANETS if en == en_name)
            planets_in_houses.append(
                {
                    "planet": en_name,
                    "planet_gr": gr_name,
                    "house": house_num,
                }
            )

        aspects = []
        for (p1, p2), label in aspects_selected_ui.items():
            code = label_to_code.get(label)
            if code is None:
                continue  # "Καμία"
            gr1 = next(gr for gr, en in PLANETS if en == p1)
            gr2 = next(gr for gr, en in PLANETS if en == p2)
            aspects.append(
                {
                    "p1": p1,
                    "p1_gr": gr1,
                    "p2": p2,
                    "p2_gr": gr2,
                    "aspect": code,
                    "aspect_label_gr": label,
                }
            )

        payload = {
            "basic_info": basic_info,
            "houses": houses,
            "planets_in_houses": planets_in_houses,
            "aspects": aspects,
        }

        st.subheader("🔍 JSON δεδομένων χάρτη (είσοδος προς ChatGPT)")
        st.code(json.dumps(payload, ensure_ascii=False, indent=2), language="json")

        st.subheader("🤖 Προσπάθεια αυτόματης παραγωγής αναφοράς με OpenAI")
        with st.spinner("Καλώ το μοντέλο..."):
            try:
                report_text = generate_report_with_openai(payload)
            except Exception as e:
                report_text = f"Παρουσιάστηκε σφάλμα κατά την κλήση του OpenAI API:\n{e}"

        st.markdown("### 📜 Αναφορά")
        st.write(report_text)


if __name__ == "__main__":
    main()
