import io
import os
import requests
import streamlit as st
from fpdf import FPDF
from ddgs import DDGS
import ollama
from gtts import gTTS

# ==========================================
# 1. PAGE SETUP & STRICT SYSTEM PROMPT
# ==========================================
st.set_page_config(
    page_title="Smart Local Guide AI",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

SYSTEM_PROMPT = """
You are a smart local guide assistant strictly restricted to local travel, places, food, area summaries, and itineraries.

GEOGRAPHIC ACCURACY & LOCALITY GUARDRAIL:
1. STRICT LOCATION CONSISTENCY: Every recommended venue MUST strictly belong to the user's requested location or neighborhood.
2. NEVER combine distant neighborhoods or different sides of the city (e.g., if the user asks for 'Hansraj College / Kamla Nagar', DO NOT include places in 'Saket', 'Gurgaon', or 'Panchkuian Road').
3. Verify addresses in the context data. If context data lists conflicting locations, discard non-matching entries and only output venues within the requested area.

STRICT DOMAIN BOUNDARY GUARDRAIL:
1. You MUST ONLY answer queries related to:
   - Local travel, tourism, landmarks, sights, and local culture.
   - Food, restaurants, cafes, markets, and nightlife.
   - Amenities (hospitals, ATMs, parks, stays, public spots).
   - Area/Neighborhood summaries and customized trip itineraries.
2. IF the user query is OUTSIDE of local travel, geography, places, food, or local guide services:
   - You MUST DECLINE to answer directly and reply EXACTLY with this response:
     "I am specialized only as a Local Guide Assistant. I can only assist with local places, food recommendations, area summaries, and travel itineraries. Please ask a question related to local guide services!"

DISTANCE & LOCATION RULES:
1. Do NOT calculate or include distances, travel times, or walk/drive estimates unless explicitly asked.
2. Always include the venue's Locality/City instead of distance.
3. At the end of every listing response where distances are omitted, append this prompt:
   '💡 Would you like to check distances to any of these places? If so, please enter your location in the sidebar or ask for distance calculations!'

GENERAL RULES:
- Always include available Ratings (★), Cuisine info, rates/prices, and Locality details in venue descriptions.
"""

# ==========================================
# 2. SESSION STATE & HISTORIES INIT
# ==========================================
if "theme_choice" not in st.session_state:
    st.session_state.theme_choice = "Warm Aesthetic (Light Brown)"

if "itinerary_history" not in st.session_state:
    st.session_state.itinerary_history = []
if "places_history" not in st.session_state:
    st.session_state.places_history = []
if "area_history" not in st.session_state:
    st.session_state.area_history = []
if "cafe_history" not in st.session_state:
    st.session_state.cafe_history = []
if "medical_history" not in st.session_state:
    st.session_state.medical_history = []

if "latest_response" not in st.session_state:
    st.session_state.latest_response = ""

# ==========================================
# 3. DYNAMIC AESTHETIC THEMES (CSS)
# ==========================================
theme_options = {
    "Warm Aesthetic (Light Brown)": {
        "bg": "#F5EFEB",
        "card": "#E8DFD8",
        "text": "#4A3B32",
        "border": "#D8C4B6",
        "accent": "#8D6E63",
    },
    "Rose Gold / Soft Pink": {
        "bg": "#FFF5F5",
        "card": "#F7E7E8",
        "text": "#4A2E35",
        "border": "#E8C5C8",
        "accent": "#C27D88",
    },
    "Sage Green / Earthy": {
        "bg": "#F4F7F4",
        "card": "#E3EAE3",
        "text": "#2C3E2C",
        "border": "#C7D5C7",
        "accent": "#6B8E6B",
    },
    "Classic Light Theme": {
        "bg": "#FFFFFF",
        "card": "#F8F9FA",
        "text": "#111111",
        "border": "#E0E0E0",
        "accent": "#0066CC",
    },
}

selected_theme = theme_options[st.session_state.theme_choice]

custom_css = f"""
<style>
    .stApp {{
        background-color: {selected_theme['bg']} !important;
        color: {selected_theme['text']} !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {selected_theme['card']} !important;
        border: 1px solid {selected_theme['border']} !important;
        border-radius: 12px !important;
        padding: 12px !important;
    }}
    p, span, label, h1, h2, h3, h4 {{
        color: {selected_theme['text']} !important;
    }}
    .stButton>button {{
        border-radius: 8px !important;
        border: 1px solid {selected_theme['border']} !important;
    }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ==========================================
# 4. HELPER FUNCTIONS, TTS & EXPORTERS
# ==========================================

def text_to_speech_bytes(text):
    """Converts text into audio MP3 bytes via gTTS."""
    try:
        clean_text = text.replace("*", "").replace("#", "")[:500]  # Read first 500 chars for smooth speech
        tts = gTTS(text=clean_text, lang='en', slow=False)
        audio_io = io.BytesIO()
        tts.write_to_fp(audio_io)
        audio_io.seek(0)
        return audio_io.read()
    except Exception:
        return None


def geocode_address(address, geoapify_key):
    """Uses Geoapify to convert location string into Lat/Lng coordinates."""
    if not geoapify_key or not geoapify_key.strip():
        return None, None
    try:
        url = f"https://api.geoapify.com/v1/geocode/search?text={address}&apiKey={geoapify_key.strip()}"
        res = requests.get(url, timeout=5).json()
        if res.get("features"):
            coords = res["features"][0]["geometry"]["coordinates"]
            return coords[1], coords[0]
    except Exception:
        pass
    return None, None


def search_foursquare_places(query, foursquare_key, user_location=None, lat=None, lon=None):
    """Fetches real-time places strictly localized to coordinates within a 3km radius."""
    if not foursquare_key or not foursquare_key.strip():
        return ""
    try:
        url = "https://places-api.foursquare.com/places/search"
        headers = {
            "accept": "application/json",
            "Authorization": foursquare_key.strip(),
            "X-Places-Api-Version": "2025-06-17",
        }

        clean_query = query.lower()
        for word in ["find", "top rated", "near me", "best", "around", "good", "suggest", "places"]:
            clean_query = clean_query.replace(word, "")
        clean_query = clean_query.strip() or "cafe"

        params = {"query": clean_query, "limit": 5}

        if lat is not None and lon is not None:
            params["ll"] = f"{lat},{lon}"
            params["radius"] = 3000
        elif user_location and user_location.strip():
            params["near"] = user_location.strip()

        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            results = res.json().get("results", [])
            places_summary = []
            for place in results:
                name = place.get("name", "Unknown")
                locality = place.get("location", {}).get("locality", "N/A")
                neighborhood = place.get("location", {}).get("neighborhood", [""])[0] if place.get("location", {}).get("neighborhood") else ""
                address = place.get("location", {}).get("formatted_address", "N/A")
                cats = [c["name"] for c in place.get("categories", []) if "name" in c]

                places_summary.append(
                    f"- **{name}** | Locality/Area: {locality} ({neighborhood}) | Address: {address} | Categories: {', '.join(cats)}"
                )
            return "\n".join(places_summary)
    except Exception:
        pass
    return ""


def search_duckduckgo(query, max_results=3):
    """Enriches context with web search via ddgs library."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
    except Exception:
        return ""


def generate_pdf(text_content):
    """Generates downloadable PDF safely handling fpdf2 parameters."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    eff_width = pdf.w - 2 * pdf.l_margin
    clean_text = text_content.encode("latin-1", "replace").decode("latin-1")
    for line in clean_text.split("\n"):
        if not line.strip():
            pdf.ln(4)
            continue
        pdf.multi_cell(
            w=eff_width,
            h=6,
            text=line,
            wrapmode="CHAR",
            new_x="LMARGIN",
            new_y="NEXT",
        )
    output = pdf.output()
    return output.encode("latin-1") if isinstance(output, str) else bytes(output)


def generate_guide_response(prompt, user_location, geo_key, fsq_key, model_name="llama3.2"):
    """Fetches location context and queries Ollama llama3.2."""
    lat, lon = None, None
    target_location = user_location

    if user_location and user_location.strip():
        lat, lon = geocode_address(user_location, geo_key)

    fsq_context = search_foursquare_places(
        prompt, fsq_key, target_location, lat, lon
    )
    web_context = search_duckduckgo(prompt)

    distance_keywords = ["near", "distance", "close", "km", "minutes", "far"]
    is_distance_requested = any(kw in prompt.lower() for kw in distance_keywords)
    location_instruction = (
        f"User located at: '{user_location}'. Include distances."
        if (is_distance_requested and user_location)
        else "Do NOT show distances/travel times unless asked. Show Locality and details only."
    )

    messages = [
        {
            "role": "system",
            "content": (
                f"{SYSTEM_PROMPT}\n\nCONTEXT INSTRUCTIONS:\n{location_instruction}\n\n"
                f"LIVE FOURSQUARE DATA:\n{fsq_context or 'No direct Foursquare results.'}\n\n"
                f"LIVE WEB SEARCH DATA:\n{web_context or 'No direct web search results.'}"
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = ollama.chat(model=model_name, messages=messages)
        return response["message"]["content"]
    except Exception as e:
        return f"⚠️ **Ollama Error:** {e}"


# ==========================================
# 5. SIDEBAR CONFIGURATION & VOICE INPUT
# ==========================================

st.sidebar.title("🎨 Theme & Voice Controls")
st.session_state.theme_choice = st.sidebar.selectbox(
    "Choose Aesthetic Theme:",
    options=list(theme_options.keys()),
    index=list(theme_options.keys()).index(st.session_state.theme_choice),
)

st.sidebar.markdown("---")
st.sidebar.header("🎙️ Voice Assistant Input")
recorded_audio = st.sidebar.audio_input("Record Voice Query")
if recorded_audio:
    st.sidebar.info("🎙️ Voice recorded! (Pass query into selected tab)")

st.sidebar.markdown("---")
st.sidebar.header("🔑 API Configurations")
geoapify_key = st.sidebar.text_input("Geoapify API Key", type="password")
foursquare_key = st.sidebar.text_input("Foursquare API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.header("📍 Location Settings")
user_location = st.sidebar.text_input(
    "Enter your location:", placeholder="e.g. Hansraj College, Delhi"
)

st.sidebar.markdown("---")
ollama_model = st.sidebar.text_input("Ollama Model Name:", value="llama3.2")

# Sidebar Export Controls
st.sidebar.markdown("---")
st.sidebar.header("📥 Global PDF/Text Exporter")
if st.session_state.latest_response:
    st.sidebar.download_button(
        label="📄 Download Text (.txt)",
        data=st.session_state.latest_response,
        file_name="latest_response.txt",
        mime="text/plain",
        key="sb_txt",
    )
    pdf_bytes_sb = generate_pdf(st.session_state.latest_response)
    st.sidebar.download_button(
        label="📕 Download PDF (.pdf)",
        data=bytes(pdf_bytes_sb),
        file_name="latest_response.pdf",
        mime="application/pdf",
        key="sb_pdf",
    )


# ==========================================
# 6. MAIN DASHBOARD WITH DEDICATED TABS
# ==========================================

st.title("📍 Smart Local Guide Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Itinerary Planner",
    "📍 Places Near You",
    "🌆 Area Summarizer",
    "☕ Quiet Work Cafes",
    "🏥 24/7 Medical Care",
])

# ------------------------------------------
# TAB 1: ITINERARY PLANNER
# ------------------------------------------
with tab1:
    st.subheader("🗺️ Customized Itinerary Planner")
    with st.form("itinerary_form"):
        col1, col2 = st.columns(2)
        with col1:
            q1_loc = st.text_input("Location / City:", value=user_location or "")
            q2_days = st.number_input(
                "Number of Days:", min_value=1, max_value=15, value=1
            )
            q3_timing = st.text_input(
                "Daily Schedule / Timing:", placeholder="e.g. 9 AM - 8 PM"
            )
            q4_food = st.selectbox(
                "Dietary Preference:",
                ["Pure Veg", "Non-Veg", "Jain Food", "Vegan", "Mixed"],
            )
        with col2:
            q5_hotel = st.select_slider(
                "Hotel Budget Range:",
                options=[
                    "Budget (Under ₹2k)",
                    "Mid-Range (₹2k-₹5k)",
                    "Luxury (₹5k+)",
                    "Day Trip",
                ],
            )
            q6_style = st.multiselect(
                "Travel Interests:",
                ["Heritage", "Food", "Shopping", "Relaxed", "Photography"],
                default=["Heritage", "Food"],
            )
            q7_group = st.selectbox(
                "Group Type:", ["Solo", "Couple", "Family", "Friends"]
            )

        submit_itin = st.form_submit_button("🚀 Generate Itinerary")

        if submit_itin and q1_loc.strip():
            prompt = f"Plan a detailed {q2_days}-Day itinerary strictly for {q1_loc}. Timing: {q3_timing}. Dietary: {q4_food}. Hotel Budget: {q5_hotel}. Interests: {', '.join(q6_style)}. Group: {q7_group}. Provide at least 2 choices (Option A / Option B) at each stage."
            with st.spinner("Crafting your customized itinerary..."):
                res = generate_guide_response(
                    prompt, q1_loc, geoapify_key, foursquare_key, ollama_model
                )
                st.session_state.latest_response = res
                st.session_state.itinerary_history.append(
                    {"id": len(st.session_state.itinerary_history) + 1, "content": res}
                )

    if st.session_state.itinerary_history:
        st.markdown("---")
        st.markdown("### 📂 Saved Itineraries")
        for item in reversed(st.session_state.itinerary_history):
            with st.expander(f"Itinerary #{item['id']}", expanded=True):
                st.markdown(item["content"])
                
                # Audio TTS Output Player
                audio_bytes = text_to_speech_bytes(item["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                col_a, col_b, col_c = st.columns([1, 1, 1])
                col_a.download_button(
                    "📄 Export Text",
                    data=item["content"],
                    file_name=f"itinerary_{item['id']}.txt",
                    key=f"itin_txt_{item['id']}",
                )
                col_b.download_button(
                    "📕 Export PDF",
                    data=bytes(generate_pdf(item["content"])),
                    file_name=f"itinerary_{item['id']}.pdf",
                    key=f"itin_pdf_{item['id']}",
                )
                if col_c.button("🗑️ Delete Entry", key=f"del_itin_{item['id']}"):
                    st.session_state.itinerary_history = [
                        h for h in st.session_state.itinerary_history if h["id"] != item["id"]
                    ]
                    st.rerun()


# ------------------------------------------
# TAB 2: PLACES NEAR YOU
# ------------------------------------------
with tab2:
    st.subheader("📍 Places Near You Finder")
    with st.form("places_form"):
        pn_loc = st.text_input(
            "Target Location / Area Name:", value=user_location or ""
        )
        pn_cats = st.multiselect(
            "Select Categories:",
            [
                "Restaurants & Food Spots",
                "Cafes & Coffee Shops",
                "Hotels & Accommodations",
                "Tourist Places",
                "Shopping Bazaars",
                "Hospitals & Clinics",
                "ATMs & Banks",
            ],
            default=["Restaurants & Food Spots", "Cafes & Coffee Shops"],
        )
        submit_pn = st.form_submit_button("🔍 Search Places")

        if submit_pn and pn_loc.strip() and pn_cats:
            prompt = f"Find nearby recommendations strictly for {', '.join(pn_cats)} near {pn_loc}. Include Ratings (★), Price/Rates, Locality, and types."
            with st.spinner("Searching nearby venues..."):
                res = generate_guide_response(
                    prompt, pn_loc, geoapify_key, foursquare_key, ollama_model
                )
                st.session_state.latest_response = res
                st.session_state.places_history.append(
                    {"id": len(st.session_state.places_history) + 1, "content": res}
                )

    if st.session_state.places_history:
        st.markdown("---")
        st.markdown("### 📂 Saved Places Searches")
        for item in reversed(st.session_state.places_history):
            with st.expander(f"Places Search #{item['id']}", expanded=True):
                st.markdown(item["content"])
                
                audio_bytes = text_to_speech_bytes(item["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                if st.button("🗑️ Delete Entry", key=f"del_pn_{item['id']}"):
                    st.session_state.places_history = [
                        h for h in st.session_state.places_history if h["id"] != item["id"]
                    ]
                    st.rerun()


# ------------------------------------------
# TAB 3: AREA SUMMARIZER
# ------------------------------------------
with tab3:
    st.subheader("🌆 Neighborhood & Area Summarizer")
    area_input = st.text_input(
        "Enter Area Name to Summarize:", value=user_location or ""
    )
    if st.button("🏙️ Summarize Area", key="btn_area") and area_input.strip():
        prompt = f"Summarize the character, stay options, amenities, food scene, and safety strictly for {area_input}."
        with st.spinner("Summarizing neighborhood..."):
            res = generate_guide_response(
                prompt, area_input, geoapify_key, foursquare_key, ollama_model
            )
            st.session_state.latest_response = res
            st.session_state.area_history.append(
                {"id": len(st.session_state.area_history) + 1, "content": res}
            )

    if st.session_state.area_history:
        st.markdown("---")
        st.markdown("### 📂 Saved Area Summaries")
        for item in reversed(st.session_state.area_history):
            with st.expander(f"Area Summary #{item['id']}", expanded=True):
                st.markdown(item["content"])
                
                audio_bytes = text_to_speech_bytes(item["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                if st.button("🗑️ Delete Entry", key=f"del_area_{item['id']}"):
                    st.session_state.area_history = [
                        h for h in st.session_state.area_history if h["id"] != item["id"]
                    ]
                    st.rerun()


# ------------------------------------------
# TAB 4: QUIET WORK CAFES
# ------------------------------------------
with tab4:
    st.subheader("☕ Quiet Work Cafes Finder")
    cafe_loc = st.text_input(
        "Enter Locality for Cafes:",
        value=user_location or "",
        key="cafe_loc_input",
    )
    if st.button("💻 Find Work Cafes", key="btn_cafe") and cafe_loc.strip():
        prompt = f"Find quiet, work-friendly cafes strictly in or near {cafe_loc} with Wi-Fi, power sockets, good seating, and coffee options."
        with st.spinner("Locating laptop-friendly cafes..."):
            res = generate_guide_response(
                prompt, cafe_loc, geoapify_key, foursquare_key, ollama_model
            )
            st.session_state.latest_response = res
            st.session_state.cafe_history.append(
                {"id": len(st.session_state.cafe_history) + 1, "content": res}
            )

    if st.session_state.cafe_history:
        st.markdown("---")
        st.markdown("### 📂 Saved Cafe Recommendations")
        for item in reversed(st.session_state.cafe_history):
            with st.expander(f"Work Cafe Search #{item['id']}", expanded=True):
                st.markdown(item["content"])
                
                audio_bytes = text_to_speech_bytes(item["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                if st.button("🗑️ Delete Entry", key=f"del_cafe_{item['id']}"):
                    st.session_state.cafe_history = [
                        h for h in st.session_state.cafe_history if h["id"] != item["id"]
                    ]
                    st.rerun()


# ------------------------------------------
# TAB 5: 24/7 MEDICAL CARE
# ------------------------------------------
with tab5:
    st.subheader("🏥 24/7 Medical Care & Hospitals")
    med_loc = st.text_input(
        "Enter Location for Emergency Services:",
        value=user_location or "",
        key="med_loc_input",
    )
    if st.button("🚑 Find Emergency Care", key="btn_med") and med_loc.strip():
        prompt = f"List 24/7 emergency multi-specialty hospitals, emergency clinics, and 24-hour pharmacies strictly near {med_loc}."
        with st.spinner("Finding emergency medical care..."):
            res = generate_guide_response(
                prompt, med_loc, geoapify_key, foursquare_key, ollama_model
            )
            st.session_state.latest_response = res
            st.session_state.medical_history.append(
                {"id": len(st.session_state.medical_history) + 1, "content": res}
            )

    if st.session_state.medical_history:
        st.markdown("---")
        st.markdown("### 📂 Saved Medical Care Searches")
        for item in reversed(st.session_state.medical_history):
            with st.expander(f"Medical Search #{item['id']}", expanded=True):
                st.markdown(item["content"])
                
                audio_bytes = text_to_speech_bytes(item["content"])
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")

                if st.button("🗑️ Delete Entry", key=f"del_med_{item['id']}"):
                    st.session_state.medical_history = [
                        h for h in st.session_state.medical_history if h["id"] != item["id"]
                    ]
                    st.rerun()