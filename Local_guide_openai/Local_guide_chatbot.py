import os
import re
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF
from gtts import gTTS

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


# ============================================================
# BASIC SETUP
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = BASE_DIR / "DejaVuSans.ttf"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Smart Local Guide",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# AI CLIENTS
# ============================================================

gemini_client = None
ollama_client = None

if GEMINI_API_KEY:
    gemini_client = OpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

if OLLAMA_API_KEY:
    ollama_client = OpenAI(
        api_key=OLLAMA_API_KEY,
        base_url="https://ollama.com/v1"
    )


# ============================================================
# MODEL SETTINGS
# ============================================================

GEMINI_MODEL = "gemini-3.6-flash"
OLLAMA_MODEL = "gpt-oss:20b-cloud"


# ============================================================
# THEME SETTINGS
# ============================================================

THEMES = {
    "Warm Aesthetic": {
        "background": "#FFF8F0",
        "surface": "#FFFDF9",
        "text": "#3D3028",
        "muted": "#75675D",
        "primary": "#B76E3D",
        "primary_hover": "#99592F",
        "secondary": "#F1E3D5",
        "border": "#E4D3C3",
        "input": "#FFFFFF",
        "input_text": "#302820",
        "tab_background": "#F4E7DB",
        "success": "#E4F1E5",
        "warning": "#FFF2D6",
        "error": "#F8DEDE",
    },

    "Rose Gold": {
        "background": "#FFF5F7",
        "surface": "#FFFFFF",
        "text": "#4A3038",
        "muted": "#806A72",
        "primary": "#B76E79",
        "primary_hover": "#995661",
        "secondary": "#F4DDE2",
        "border": "#E6C7CE",
        "input": "#FFFFFF",
        "input_text": "#3D2930",
        "tab_background": "#F7E7EA",
        "success": "#E4F1E5",
        "warning": "#FFF2D6",
        "error": "#F8DEDE",
    },

    "Sage Green": {
        "background": "#F4F7F1",
        "surface": "#FFFFFF",
        "text": "#304034",
        "muted": "#667369",
        "primary": "#668B6B",
        "primary_hover": "#527257",
        "secondary": "#E0EADF",
        "border": "#CCD8CB",
        "input": "#FFFFFF",
        "input_text": "#29352C",
        "tab_background": "#E8EFE6",
        "success": "#DDEEDF",
        "warning": "#FFF2D6",
        "error": "#F8DEDE",
    },

    "Classic Light": {
        "background": "#F5F7FA",
        "surface": "#FFFFFF",
        "text": "#20242A",
        "muted": "#68717C",
        "primary": "#3F6FA8",
        "primary_hover": "#315A8C",
        "secondary": "#E8ECF1",
        "border": "#D7DCE2",
        "input": "#FFFFFF",
        "input_text": "#20242A",
        "tab_background": "#EEF1F5",
        "success": "#E0F0E4",
        "warning": "#FFF1D6",
        "error": "#F8DEDE",
    },

    "Dark Theme": {
        "background": "#101318",
        "surface": "#1A1F27",
        "text": "#F5F7FA",
        "muted": "#C3CBD6",
        "primary": "#8AB4F8",
        "primary_hover": "#A9C7FA",
        "secondary": "#29313D",
        "border": "#3A4554",
        "input": "#222933",
        "input_text": "#FFFFFF",
        "tab_background": "#202733",
        "success": "#243A2D",
        "warning": "#3E351F",
        "error": "#40272B",
    },
}


# ============================================================
# SIDEBAR / THEME
# ============================================================

if "theme" not in st.session_state:
    st.session_state.theme = "Warm Aesthetic"

with st.sidebar:
    st.markdown("## 🧭 Smart Local Guide")

    selected_theme = st.selectbox(
        "🎨 Choose Theme",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme)
    )

    st.session_state.theme = selected_theme


theme = THEMES[st.session_state.theme]


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>

    /* ---------- MAIN APP ---------- */

    .stApp {{
        background-color: {theme["background"]};
        color: {theme["text"]};
    }}

    .main {{
        background-color: {theme["background"]};
    }}

    /* ---------- TEXT ---------- */

    h1, h2, h3, h4, h5, h6 {{
        color: {theme["text"]} !important;
    }}

    p, span, label, div {{
        color: {theme["text"]};
    }}

    .stCaption {{
        color: {theme["muted"]} !important;
    }}

    /* ---------- SIDEBAR ---------- */

    section[data-testid="stSidebar"] {{
        background-color: {theme["surface"]};
        border-right: 1px solid {theme["border"]};
    }}

    section[data-testid="stSidebar"] * {{
        color: {theme["text"]} !important;
    }}

    /* ---------- INPUTS ---------- */

    div[data-baseweb="input"],
    div[data-baseweb="select"],
    div[data-baseweb="textarea"] {{
        background-color: {theme["input"]} !important;
        border-color: {theme["border"]} !important;
    }}

    input,
    textarea {{
        background-color: {theme["input"]} !important;
        color: {theme["input_text"]} !important;
        caret-color: {theme["input_text"]} !important;
    }}

    input::placeholder,
    textarea::placeholder {{
        color: {theme["muted"]} !important;
    }}

    /* ---------- SELECTBOX ---------- */

    div[data-baseweb="select"] > div {{
        background-color: {theme["input"]} !important;
        color: {theme["input_text"]} !important;
        border-color: {theme["border"]} !important;
    }}

    div[data-baseweb="select"] span {{
        color: {theme["input_text"]} !important;
    }}

    /* ---------- MULTISELECT ---------- */

    div[data-baseweb="select"] div {{
        color: {theme["input_text"]} !important;
    }}

    div[data-baseweb="tag"] {{
        background-color: {theme["secondary"]} !important;
    }}

    div[data-baseweb="tag"] span {{
        color: {theme["text"]} !important;
    }}

    /* ---------- DROPDOWN MENU ---------- */

    ul[role="listbox"],
    div[role="listbox"] {{
        background-color: {theme["surface"]} !important;
        color: {theme["text"]} !important;
        border-color: {theme["border"]} !important;
    }}

    li[role="option"] {{
        background-color: {theme["surface"]} !important;
        color: {theme["text"]} !important;
    }}

    li[role="option"]:hover {{
        background-color: {theme["secondary"]} !important;
    }}

    /* ---------- TABS ---------- */

    button[data-baseweb="tab"] {{
        background-color: {theme["tab_background"]} !important;
        color: {theme["text"]} !important;
        border-color: {theme["border"]} !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {theme["primary"]} !important;
        border-bottom-color: {theme["primary"]} !important;
    }}

    /* ---------- BUTTONS ---------- */

    .stButton > button {{
        background-color: {theme["primary"]};
        color: #FFFFFF !important;
        border: 1px solid {theme["primary"]};
        border-radius: 8px;
        font-weight: 600;
    }}

    .stButton > button:hover {{
        background-color: {theme["primary_hover"]};
        border-color: {theme["primary_hover"]};
        color: #FFFFFF !important;
    }}

    /* ---------- EXPANDERS ---------- */

    div[data-testid="stExpander"] {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 10px;
    }}

    div[data-testid="stExpander"] summary {{
        color: {theme["text"]} !important;
    }}

    /* ---------- ALERTS ---------- */

    div[data-testid="stAlert"] {{
        color: {theme["text"]} !important;
    }}

    /* ---------- MARKDOWN CONTAINERS ---------- */

    .guide-card {{
        background-color: {theme["surface"]};
        border: 1px solid {theme["border"]};
        border-radius: 14px;
        padding: 20px;
        margin: 10px 0;
    }}

    .hero-title {{
        font-size: 42px;
        font-weight: 800;
        color: {theme["text"]};
        margin-bottom: 5px;
    }}

    .hero-subtitle {{
        font-size: 18px;
        color: {theme["muted"]};
        margin-bottom: 20px;
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE
# ============================================================

if "itinerary_history" not in st.session_state:
    st.session_state.itinerary_history = []

if "places_history" not in st.session_state:
    st.session_state.places_history = []

if "area_history" not in st.session_state:
    st.session_state.area_history = []

if "cafes_history" not in st.session_state:
    st.session_state.cafes_history = []

if "medical_history" not in st.session_state:
    st.session_state.medical_history = []


# ============================================================
# OPTIONS
# ============================================================

INTEREST_OPTIONS = [
    "🏛️ History",
    "🎨 Art & Museums",
    "🌳 Parks & Nature",
    "🏖️ Beaches",
    "🏔️ Adventure",
    "🛍️ Shopping",
    "🍜 Food",
    "☕ Cafés",
    "🍰 Bakeries & Desserts",
    "🌃 Nightlife",
    "🎵 Music",
    "🎬 Movies & Entertainment",
    "📸 Photography",
    "🏙️ Architecture",
    "🛕 Religious Places",
    "👨‍👩‍👧 Family Activities",
    "🎢 Amusement Parks",
    "🏞️ Scenic Places",
    "🧘 Wellness & Relaxation",
    "⚽ Sports",
    "📚 Bookstores & Libraries",
    "🎭 Theatre & Performing Arts",
    "💻 Work-Friendly Places",
    "💎 Hidden Gems",
]


FOOD_MAIN_OPTIONS = [
    "🥬 Vegetarian",
    "🍗 Non-Vegetarian",
    "🌱 Vegan",
    "🍰 Bakery & Café",
    "🍽️ No Specific Preference",
]


CUISINE_OPTIONS = [
    "🇮🇳 Indian",
    "🥘 North Indian",
    "🌶️ South Indian",
    "🍛 Mughlai",
    "🥟 Chinese",
    "🍝 Italian",
    "🍣 Japanese",
    "🥢 Korean",
    "🌮 Mexican",
    "🥙 Middle Eastern",
    "🍕 Continental",
    "🍔 American",
    "🥗 Healthy / Salad",
    "🍜 Thai",
    "🥘 Mediterranean",
    "🌍 International",
]


BAKERY_OPTIONS = [
    "☕ Coffee",
    "🍵 Tea",
    "🎂 Cakes",
    "🧁 Cupcakes",
    "🥐 Croissants",
    "🍪 Cookies",
    "🍩 Donuts",
    "🍰 Pastries",
    "🍫 Desserts",
    "🍨 Ice Cream",
    "🥪 Sandwiches",
    "🥯 Bagels",
    "🥖 Bread & Artisan Bakery",
    "🍮 Traditional Sweets",
]


TRANSPORT_OPTIONS = [
    "🚶 Walking",
    "🚇 Metro",
    "🚌 Bus",
    "🚕 Taxi / Cab",
    "🛺 Auto Rickshaw",
    "🚗 Car",
    "🏍️ Bike / Scooter",
    "🚲 Bicycle",
    "🚆 Local Train",
]


ADDITIONAL_PREFERENCE_OPTIONS = [
    "📸 Good Photography Spots",
    "🌅 Sunrise / Sunset",
    "🌙 Night Activities",
    "👨‍👩‍👧 Family Friendly",
    "♿ Accessibility Friendly",
    "💰 Budget Friendly",
    "⭐ Popular / Must Visit",
    "💎 Local / Hidden Places",
    "🛍️ Shopping Time",
    "☕ Café Breaks",
    "🍽️ Restaurant Stops",
    "🏨 Hotel / Rest Break",
]


PLACE_CATEGORIES = {
    "🍴 Food & Restaurants": "restaurants and food places",
    "☕ Cafés": "cafes and coffee shops",
    "🍰 Bakeries": "bakeries, cake shops and dessert shops",
    "🏨 Hotels": "hotels and accommodation",
    "🏛️ Tourist Spots": "tourist attractions",
    "🛍️ Shopping": "shopping malls and shopping markets",
    "🏥 Hospitals": "hospitals and medical centers",
    "💊 Pharmacies": "pharmacies and medicine stores",
    "🏧 ATMs": "ATMs and cash withdrawal points",
    "🛕 Cultural Landmarks": "cultural and historical landmarks",
    "🌳 Parks & Nature": "parks, gardens and nature places",
    "🎭 Entertainment": "entertainment venues",
    "📚 Bookstores": "bookstores and libraries",
    "💎 Hidden Gems": "lesser-known local attractions",
}


# ============================================================
# HELPER: CLEAN TEXT
# ============================================================

def clean_text(text):
    if not text:
        return ""

    text = str(text)

    # Remove accidental markdown code fences
    text = text.replace("```text", "")
    text = text.replace("```markdown", "")
    text = text.replace("```", "")

    return text.strip()


# ============================================================
# AI GENERATION
# ============================================================

def generate_response(prompt, temperature=0.7):
    """
    Gemini is the primary provider.
    Ollama Cloud is automatically used if Gemini fails.
    """

    errors = []

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------

    if gemini_client:
        try:
            response = gemini_client.chat.completions.create(
                model=GEMINI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Smart Local Guide, an intelligent travel "
                            "and local-area assistant. Give practical, clear, "
                            "well-organized information. Never invent exact "
                            "facts when web information is supplied."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
            )

            return clean_text(response.choices[0].message.content)

        except Exception as e:
            errors.append(f"Gemini: {str(e)}")

    # --------------------------------------------------------
    # OLLAMA CLOUD BACKUP
    # --------------------------------------------------------

    if ollama_client:
        try:
            response = ollama_client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Smart Local Guide, an intelligent travel "
                            "and local-area assistant. Give practical, clear, "
                            "well-organized information."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
            )

            return clean_text(response.choices[0].message.content)

        except Exception as e:
            errors.append(f"Ollama: {str(e)}")

    if not GEMINI_API_KEY and not OLLAMA_API_KEY:
        return (
            "⚠️ No AI API key is configured. "
            "Please add GEMINI_API_KEY or OLLAMA_API_KEY to your .env file."
        )

    return (
        "⚠️ Both AI services failed.\n\n"
        + "\n".join(errors)
    )


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(query, max_results=6):
    """
    Search the web using DuckDuckGo.
    """

    results = []

    try:
        with DDGS() as ddgs:
            search_results = ddgs.text(
                query,
                max_results=max_results
            )

            for result in search_results:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("href", ""),
                    "body": result.get("body", ""),
                })

    except Exception as e:
        results.append({
            "title": "Search error",
            "url": "",
            "body": str(e)
        })

    return results


def format_search_results(results):
    text = ""

    for index, result in enumerate(results, start=1):
        text += (
            f"\nSOURCE {index}\n"
            f"Title: {result.get('title', '')}\n"
            f"URL: {result.get('url', '')}\n"
            f"Description: {result.get('body', '')}\n"
        )

    return text


# ============================================================
# PDF CREATION
# ============================================================

def create_pdf(title, content):
    """
    Create a Unicode-compatible PDF.

    DejaVuSans.ttf must be placed beside this Python file.
    """

    if not FONT_PATH.exists():
        raise FileNotFoundError(
            f"DejaVuSans.ttf was not found at: {FONT_PATH}"
        )

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.add_page()

    # Register Unicode font
    pdf.add_font(
        "DejaVu",
        "",
        str(FONT_PATH)
    )

    # Title
    pdf.set_font(
        "DejaVu",
        "",
        18
    )

    pdf.multi_cell(
        0,
        10,
        clean_text(title)
    )

    pdf.ln(5)

    # Content
    pdf.set_font(
        "DejaVu",
        "",
        11
    )

    pdf.multi_cell(
        0,
        7,
        clean_text(content)
    )

    return bytes(pdf.output())


# ============================================================
# TEXT TO SPEECH
# ============================================================

def create_audio(text):
    try:
        audio_path = BASE_DIR / "smart_local_guide_audio.mp3"

        tts = gTTS(
            text=clean_text(text),
            lang="en"
        )

        tts.save(str(audio_path))

        with open(audio_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        try:
            audio_path.unlink()
        except Exception:
            pass

        return audio_bytes

    except Exception:
        return None


# ============================================================
# HISTORY DISPLAY
# ============================================================

def show_history(history, history_name):
    if not history:
        st.info("No previous results yet.")
        return

    st.markdown("### 📚 Previous Results")

    for index, item in enumerate(reversed(history), start=1):

        title = item.get(
            "title",
            f"Result {index}"
        )

        content = item.get(
            "content",
            ""
        )

        with st.expander(
            f"📌 {title}",
            expanded=False
        ):

            st.markdown(content)

            col1, col2 = st.columns(2)

            # PDF
            with col1:
                try:
                    pdf_bytes = create_pdf(
                        title,
                        content
                    )

                    st.download_button(
                        "📄 Download PDF",
                        data=pdf_bytes,
                        file_name=f"{history_name}_{index}.pdf",
                        mime="application/pdf",
                        key=f"{history_name}_pdf_{index}"
                    )

                except Exception as e:
                    st.error(
                        f"PDF creation failed: {e}"
                    )

            # Audio
            with col2:
                if st.button(
                    "🔊 Listen",
                    key=f"{history_name}_audio_button_{index}"
                ):

                    with st.spinner("Creating audio..."):
                        audio = create_audio(content)

                    if audio:
                        st.audio(
                            audio,
                            format="audio/mp3"
                        )
                    else:
                        st.error(
                            "Unable to create audio."
                        )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="hero-title">🧭 Smart Local Guide</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="hero-subtitle">'
    "Plan trips, discover places, understand neighborhoods, "
    "find work-friendly cafés and locate medical services."
    "</div>",
    unsafe_allow_html=True
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🗺️ Itinerary Planner",
        "📍 Places Near You",
        "🏘️ Area Summarizer",
        "☕ Quiet Work Cafés",
        "🏥 24/7 Medical Care",
    ]
)


# ============================================================
# TAB 1 — ITINERARY PLANNER
# ============================================================

with tab1:

    st.header("🗺️ Personalized Itinerary Planner")

    st.write(
        "Create a personalized travel plan based on your "
        "location, interests, budget, food preferences and "
        "transport choices."
    )

    city = st.text_input(
        "📍 City / Neighborhood",
        placeholder="Example: Connaught Place, Delhi"
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        duration = st.number_input(
            "📅 Duration (days)",
            min_value=1,
            max_value=30,
            value=1,
            step=1
        )

    with col2:
        budget = st.number_input(
            "💰 Budget (₹)",
            min_value=0,
            value=3000,
            step=500
        )

    with col3:
        radius = st.number_input(
            "📏 Radius (km)",
            min_value=1,
            max_value=50,
            value=3,
            step=1
        )

    interests = st.multiselect(
        "🎯 What are you interested in?",
        INTEREST_OPTIONS
    )

    st.markdown("### 🍽️ Food Preferences")

    food_main = st.multiselect(
        "Food Type",
        FOOD_MAIN_OPTIONS
    )

    cuisine = st.multiselect(
        "Cuisine Preferences",
        CUISINE_OPTIONS
    )

    bakery = st.multiselect(
        "Bakery / Café Preferences",
        BAKERY_OPTIONS
    )

    col1, col2 = st.columns(2)

    with col1:
        group_type = st.selectbox(
            "👥 Traveling With",
            [
                "👤 Solo",
                "💑 Couple",
                "👨‍👩‍👧 Family",
                "👫 Friends",
                "💼 Work / Business",
                "🎓 Students",
            ]
        )

    with col2:
        pace = st.selectbox(
            "🏃 Travel Pace",
            [
                "🐢 Relaxed",
                "🚶 Balanced",
                "🏃 Fast-Paced",
            ]
        )

    transport = st.multiselect(
        "🚗 Preferred Transport",
        TRANSPORT_OPTIONS
    )

    additional_preferences = st.multiselect(
        "✨ Additional Preferences",
        ADDITIONAL_PREFERENCE_OPTIONS
    )

    if st.button(
        "✨ Generate My Itinerary",
        use_container_width=True
    ):

        if not city.strip():
            st.warning(
                "Please enter a city or neighborhood."
            )

        else:

            with st.status(
                "🔎 Searching and generating your itinerary...",
                expanded=True
            ) as status:

                st.write("Searching for relevant local information...")

                search_query = (
                    f"best places to visit in {city} "
                    f"tourist attractions restaurants cafes "
                    f"things to do"
                )

                results = web_search(
                    search_query,
                    max_results=8
                )

                source_text = format_search_results(
                    results
                )

                st.write("Creating personalized itinerary...")

                prompt = f"""
Create a practical personalized travel itinerary.

LOCATION:
{city}

DURATION:
{duration} day(s)

BUDGET:
₹{budget}

SEARCH RADIUS:
{radius} km

INTERESTS:
{", ".join(interests) if interests else "No specific interests"}

FOOD TYPE:
{", ".join(food_main) if food_main else "No specific preference"}

CUISINES:
{", ".join(cuisine) if cuisine else "No specific cuisine preference"}

BAKERY / CAFE PREFERENCES:
{", ".join(bakery) if bakery else "No specific bakery preference"}

GROUP:
{group_type}

PACE:
{pace}

TRANSPORT:
{", ".join(transport) if transport else "Flexible"}

ADDITIONAL PREFERENCES:
{", ".join(additional_preferences) if additional_preferences else "None"}

IMPORTANT:
- Keep places within approximately {radius} km where possible.
- Make the itinerary realistic.
- Avoid unnecessarily long travel between locations.
- Consider the selected pace.
- Consider the budget.
- Include food stops when relevant.
- Clearly separate each day.
- Include morning, afternoon and evening suggestions.
- Include practical transport suggestions.
- Mention approximate spending when useful.
- Do not invent exact opening hours.
- If information is uncertain, say so.
- Do not use tables.

WEB INFORMATION:
{source_text}
"""

                answer = generate_response(
                    prompt
                )

                status.update(
                    label="✅ Itinerary generated!",
                    state="complete"
                )

            st.markdown("## 🗓️ Your Itinerary")

            st.markdown(
                '<div class="guide-card">',
                unsafe_allow_html=True
            )

            st.markdown(answer)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            # Save history
            st.session_state.itinerary_history.append(
                {
                    "title": f"{city} — {duration} Day Itinerary",
                    "content": answer
                }
            )

            # Immediate actions
            col1, col2 = st.columns(2)

            with col1:
                try:
                    pdf = create_pdf(
                        f"{city} — Travel Itinerary",
                        answer
                    )

                    st.download_button(
                        "📄 Download PDF",
                        data=pdf,
                        file_name="itinerary.pdf",
                        mime="application/pdf",
                        key="itinerary_download"
                    )
                except Exception as e:
                    st.error(f"PDF error: {e}")

            with col2:
                if st.button(
                    "🔊 Listen to Itinerary",
                    key="itinerary_listen"
                ):

                    with st.spinner(
                        "Creating audio..."
                    ):
                        audio = create_audio(answer)

                    if audio:
                        st.audio(
                            audio,
                            format="audio/mp3"
                        )

    st.divider()

    show_history(
        st.session_state.itinerary_history,
        "itinerary"
    )


# ============================================================
# TAB 2 — PLACES NEAR YOU
# ============================================================

with tab2:

    st.header("📍 Find Places Near You")

    st.write(
        "Select multiple categories and discover multiple "
        "places for each category."
    )

    location = st.text_input(
        "📍 Enter Location",
        placeholder="Example: Hauz Khas, Delhi",
        key="places_location"
    )

    selected_categories = st.multiselect(
        "🔎 Select Place Categories",
        list(PLACE_CATEGORIES.keys()),
        default=[
            "🍴 Food & Restaurants",
            "☕ Cafés"
        ]
    )

    result_count = st.slider(
        "Number of results per category",
        min_value=2,
        max_value=10,
        value=5
    )

    if st.button(
        "🔎 Find Places",
        use_container_width=True
    ):

        if not location.strip():
            st.warning(
                "Please enter a location."
            )

        elif not selected_categories:
            st.warning(
                "Please select at least one category."
            )

        else:

            with st.status(
                "🔎 Searching for places...",
                expanded=True
            ) as status:

                all_results = []
                seen_urls = set()

                for category in selected_categories:

                    description = PLACE_CATEGORIES[
                        category
                    ]

                    st.write(
                        f"Searching {category}..."
                    )

                    query = (
                        f"{description} near {location}"
                    )

                    results = web_search(
                        query,
                        max_results=result_count
                    )

                    for result in results:

                        url = result.get(
                            "url",
                            ""
                        )

                        if url and url not in seen_urls:

                            seen_urls.add(url)

                            all_results.append(
                                {
                                    "category": category,
                                    **result
                                }
                            )

                source_text = ""

                for result in all_results:

                    source_text += (
                        f"\nCATEGORY: "
                        f"{result['category']}\n"
                        f"TITLE: "
                        f"{result['title']}\n"
                        f"URL: "
                        f"{result['url']}\n"
                        f"DESCRIPTION: "
                        f"{result['body']}\n"
                    )

                st.write(
                    "Organizing results..."
                )

                prompt = f"""
You are helping a user discover places near:

LOCATION:
{location}

The user selected these categories:

{", ".join(selected_categories)}

Organize the search results by category.

For every category:
- Give several useful results.
- Include the place/business name.
- Give a short explanation.
- Include the available URL.
- Do not invent ratings, prices, addresses or opening hours.
- Clearly say when information is unavailable.
- Do not use a table.
- Keep the answer easy to scan.

SEARCH RESULTS:
{source_text}
"""

                answer = generate_response(
                    prompt
                )

                status.update(
                    label="✅ Places found!",
                    state="complete"
                )

            st.markdown("## 📍 Results")

            st.markdown(
                '<div class="guide-card">',
                unsafe_allow_html=True
            )

            st.markdown(answer)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            st.session_state.places_history.append(
                {
                    "title": f"Places near {location}",
                    "content": answer
                }
            )

    st.divider()

    show_history(
        st.session_state.places_history,
        "places"
    )


# ============================================================
# TAB 3 — AREA SUMMARIZER
# ============================================================

with tab3:

    st.header("🏘️ Area / Neighborhood Summarizer")

    st.write(
        "Understand what an area is like by looking at "
        "restaurants, cafés, ATMs, hospitals, attractions "
        "and other nearby amenities."
    )

    area = st.text_input(
        "📍 Enter Neighborhood / ZIP / Area",
        placeholder="Example: Saket, Delhi",
        key="area_location"
    )

    area_radius = st.slider(
        "📏 Search radius",
        min_value=1,
        max_value=10,
        value=3,
        key="area_radius"
    )

    if st.button(
        "🏘️ Summarize Area",
        use_container_width=True
    ):

        if not area.strip():
            st.warning(
                "Please enter an area."
            )

        else:

            with st.status(
                "🔎 Analyzing the area...",
                expanded=True
            ) as status:

                categories = [
                    "restaurants",
                    "cafes",
                    "ATMs",
                    "hospitals",
                    "pharmacies",
                    "tourist attractions",
                    "shopping",
                    "parks",
                    "public transport",
                ]

                area_results = []

                for category in categories:

                    st.write(
                        f"Checking {category}..."
                    )

                    query = (
                        f"{category} near {area}"
                    )

                    results = web_search(
                        query,
                        max_results=4
                    )

                    area_results.extend(
                        results
                    )

                source_text = format_search_results(
                    area_results
                )

                st.write(
                    "Generating area summary..."
                )

                prompt = f"""
Analyze the neighborhood:

{area}

Search radius:
{area_radius} km

Based on the provided information, write a practical
neighborhood summary.

Discuss:

1. Overall character of the area
2. Food and restaurants
3. Cafés
4. Shopping
5. Hospitals and pharmacies
6. ATMs and convenience
7. Attractions
8. Parks and nature
9. Transport accessibility
10. Possible advantages
11. Possible limitations
12. Who might enjoy staying or spending time here

Do not make unsupported claims.
Do not invent exact distances or opening hours.
Clearly distinguish search information from reasonable interpretation.
Do not use tables.

SEARCH INFORMATION:
{source_text}
"""

                answer = generate_response(
                    prompt
                )

                status.update(
                    label="✅ Area summary ready!",
                    state="complete"
                )

            st.markdown("## 🏘️ Area Summary")

            st.markdown(
                '<div class="guide-card">',
                unsafe_allow_html=True
            )

            st.markdown(answer)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            st.session_state.area_history.append(
                {
                    "title": f"Area Summary — {area}",
                    "content": answer
                }
            )

    st.divider()

    show_history(
        st.session_state.area_history,
        "area"
    )


# ============================================================
# TAB 4 — QUIET WORK CAFES
# ============================================================

with tab4:

    st.header("☕ Quiet Work Cafés")

    st.write(
        "Find cafés suitable for studying, working or "
        "spending a few productive hours."
    )

    cafe_location = st.text_input(
        "📍 Location",
        placeholder="Example: South Campus, Delhi",
        key="cafe_location"
    )

    cafe_amenities = st.multiselect(
        "💻 Preferred Amenities",
        [
            "📶 Wi-Fi",
            "🔌 Charging Points",
            "🤫 Quiet Environment",
            "🪑 Comfortable Seating",
            "❄️ Air Conditioning",
            "🌿 Outdoor Seating",
            "☕ Good Coffee",
            "🍰 Desserts / Bakery",
            "🕐 Long Working Hours",
            "💰 Budget Friendly",
        ]
    )

    if st.button(
        "☕ Find Work-Friendly Cafés",
        use_container_width=True
    ):

        if not cafe_location.strip():
            st.warning(
                "Please enter a location."
            )

        else:

            with st.status(
                "☕ Searching for suitable cafés...",
                expanded=True
            ) as status:

                query = (
                    f"quiet cafes for working studying "
                    f"wifi charging near {cafe_location}"
                )

                results = web_search(
                    query,
                    max_results=10
                )

                source_text = format_search_results(
                    results
                )

                prompt = f"""
Find and organize cafés suitable for working or studying.

LOCATION:
{cafe_location}

PREFERRED AMENITIES:
{", ".join(cafe_amenities) if cafe_amenities else "No specific preference"}

Based on the search results:

- Identify suitable cafés.
- Explain why each may be suitable for work/study.
- Mention Wi-Fi, charging, seating or working hours only
  when supported by the search information.
- Do not invent amenities.
- Mention uncertainty when information is unclear.
- Do not use tables.

SEARCH RESULTS:
{source_text}
"""

                answer = generate_response(
                    prompt
                )

                status.update(
                    label="✅ Café recommendations ready!",
                    state="complete"
                )

            st.markdown("## ☕ Work-Friendly Cafés")

            st.markdown(
                '<div class="guide-card">',
                unsafe_allow_html=True
            )

            st.markdown(answer)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            st.session_state.cafes_history.append(
                {
                    "title": f"Work Cafés — {cafe_location}",
                    "content": answer
                }
            )

    st.divider()

    show_history(
        st.session_state.cafes_history,
        "cafes"
    )


# ============================================================
# TAB 5 — 24/7 MEDICAL CARE
# ============================================================

with tab5:

    st.header("🏥 24/7 Medical Care")

    st.write(
        "Search for hospitals, emergency departments, urgent "
        "care centers and late-night pharmacies."
    )

    medical_location = st.text_input(
        "📍 Location",
        placeholder="Example: Dwarka, Delhi",
        key="medical_location"
    )

    medical_type = st.multiselect(
        "🏥 What do you need?",
        [
            "🚑 24/7 Hospitals",
            "🚨 Emergency Departments",
            "🩺 Urgent Care",
            "💊 Late-Night Pharmacies",
            "🧑‍⚕️ Clinics",
            "🧪 Diagnostic Centers",
        ],
        default=[
            "🚑 24/7 Hospitals",
            "🚨 Emergency Departments",
        ]
    )

    if st.button(
        "🏥 Find Medical Services",
        use_container_width=True
    ):

        if not medical_location.strip():
            st.warning(
                "Please enter a location."
            )

        elif not medical_type:
            st.warning(
                "Please select at least one service."
            )

        else:

            with st.status(
                "🏥 Searching for medical services...",
                expanded=True
            ) as status:

                search_results = []

                for service in medical_type:

                    st.write(
                        f"Searching {service}..."
                    )

                    query = (
                        f"{service} near "
                        f"{medical_location}"
                    )

                    results = web_search(
                        query,
                        max_results=6
                    )

                    search_results.extend(
                        results
                    )

                source_text = format_search_results(
                    search_results
                )

                prompt = f"""
Find medical services near:

{medical_location}

Requested services:
{", ".join(medical_type)}

Organize the results clearly.

For each useful result:
- Name
- Type of service
- Available location information
- Website or source URL if available
- Explain whether it is described as 24/7 or emergency care
- Do not claim that a facility is open 24/7 unless the source supports it.
- Do not invent phone numbers.
- For emergencies, remind the user to contact the appropriate
  local emergency service rather than relying only on this app.
- Do not use tables.

SEARCH RESULTS:
{source_text}
"""

                answer = generate_response(
                    prompt
                )

                status.update(
                    label="✅ Medical search complete!",
                    state="complete"
                )

            st.markdown(
                "## 🏥 Medical Services"
            )

            st.markdown(
                '<div class="guide-card">',
                unsafe_allow_html=True
            )

            st.markdown(answer)

            st.markdown(
                "</div>",
                unsafe_allow_html=True
            )

            st.session_state.medical_history.append(
                {
                    "title": (
                        f"Medical Services — "
                        f"{medical_location}"
                    ),
                    "content": answer
                }
            )

    st.divider()

    show_history(
        st.session_state.medical_history,
        "medical"
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    f"""
    <div style="
        text-align:center;
        color:{theme["muted"]};
        padding:15px;
        font-size:14px;
    ">
        🧭 Smart Local Guide
        <br>
        AI-powered local discovery and itinerary planning
    </div>
    """,
    unsafe_allow_html=True
)