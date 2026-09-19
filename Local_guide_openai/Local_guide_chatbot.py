import os
import io
import time

import streamlit as st
from openai import OpenAI
from fpdf import FPDF
from gtts import gTTS


# ==============================================================================
# 1. PAGE & THEME CONFIGURATION
# ==============================================================================

st.set_page_config(
    page_title="Smart Local Guide",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded"
)


THEMES = {
    "Warm Aesthetic": {
        "primaryColor": "#D97706",
        "backgroundColor": "#FFFBEB",
        "secondaryBackgroundColor": "#FEF3C7",
        "textColor": "#78350F",
    },

    "Rose Gold": {
        "primaryColor": "#E11D48",
        "backgroundColor": "#FFF1F2",
        "secondaryBackgroundColor": "#FFE4E6",
        "textColor": "#881337",
    },

    "Sage Green": {
        "primaryColor": "#059669",
        "backgroundColor": "#ECFDF5",
        "secondaryBackgroundColor": "#D1FAE5",
        "textColor": "#065F46",
    },

    "Classic Light": {
        "primaryColor": "#2563EB",
        "backgroundColor": "#FFFFFF",
        "secondaryBackgroundColor": "#F3F4F6",
        "textColor": "#1F2937",
    }
}


# Theme selector
selected_theme = st.sidebar.selectbox(
    "🎨 Choose Theme",
    list(THEMES.keys()),
    index=0
)

theme_colors = THEMES[selected_theme]


# Dynamic CSS
st.markdown(
    f"""
    <style>

    .stApp {{
        background-color: {theme_colors['backgroundColor']};
        color: {theme_colors['textColor']};
    }}

    .stButton>button {{
        background-color: {theme_colors['primaryColor']};
        color: white;
        border-radius: 8px;
        border: none;
    }}

    .stSidebar {{
        background-color: {theme_colors['secondaryBackgroundColor']};
    }}

    </style>
    """,
    unsafe_allow_html=True
)


# ==============================================================================
# 2. SESSION STATE
# ==============================================================================

# Each feature has its own history.

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


# ==============================================================================
# 3. GEMINI CLIENT
# ==============================================================================

def get_gemini_client(user_api_key=""):
    """
    Create Gemini client using Google's OpenAI-compatible API.
    """

    api_key = os.environ.get("GEMINI_API_KEY") or user_api_key

    if not api_key:
        st.sidebar.error(
            "⚠️ Please provide a Google AI Studio Gemini API Key "
            "in the sidebar or GEMINI_API_KEY environment variable."
        )
        return None

    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


# ==============================================================================
# 4. GEMINI RESPONSE FUNCTION
# ==============================================================================

def generate_response(system_prompt, user_prompt, model):
    """
    Generate a response from Gemini.

    Includes:
    - Automatic retry
    - Fallback models
    - Handling of temporary 503 errors
    """

    if not client:
        return None

    # First try the model selected by the user.
    # Then try fallback models if a temporary 503 error occurs.

    fallback_models = [
        model,
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]

    # Remove duplicates
    models_to_try = list(dict.fromkeys(fallback_models))

    last_error = None

    for current_model in models_to_try:

        for attempt in range(2):

            try:

                response = client.chat.completions.create(
                    model=current_model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )

                return response.choices[0].message.content

            except Exception as e:

                last_error = e
                error_text = str(e)

                # Temporary Gemini server overload
                if "503" in error_text or "UNAVAILABLE" in error_text:

                    if attempt == 0:
                        time.sleep(2)
                        continue

                    # Try next fallback model
                    break

                # Authentication / bad request / other errors
                # should not silently switch models.
                raise e

    st.error(
        "⚠️ Gemini is temporarily unavailable. "
        "Please try again in a few moments."
    )

    if last_error:
        st.caption(
            f"Last error: {last_error}"
        )

    return None


# ==============================================================================
# 5. TEXT TO SPEECH
# ==============================================================================

def generate_tts_audio(text):
    """
    Generate audio using gTTS.
    """

    try:

        clean_text = (
            text
            .replace("*", "")
            .replace("#", "")
            .replace("-", "")
        )[:400]

        tts = gTTS(
            text=clean_text,
            lang="en",
            slow=False
        )

        fp = io.BytesIO()

        tts.write_to_fp(fp)

        fp.seek(0)

        return fp.read()

    except Exception as e:

        st.warning(
            f"Audio generation failed: {e}"
        )

        return None


# ==============================================================================
# 6. PDF GENERATION
# ==============================================================================

def generate_pdf_bytes(title, content):
    """
    Generate a simple PDF document.
    """

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Helvetica",
        size=16,
        style="B"
    )

    pdf.cell(
        200,
        10,
        txt=title,
        ln=1,
        align="C"
    )

    pdf.ln(5)

    pdf.set_font(
        "Helvetica",
        size=10
    )

    clean_content = (
        content
        .encode("latin-1", "replace")
        .decode("latin-1")
    )

    pdf.multi_cell(
        0,
        6,
        txt=clean_content
    )

    return bytes(pdf.output())


# ==============================================================================
# 7. DUCKDUCKGO WEB SEARCH
# ==============================================================================

try:

    from duckduckgo_search import DDGS

except ImportError:

    try:
        from ddgs import DDGS

    except ImportError:

        DDGS = None


def web_search(query):
    """
    Search the web using DuckDuckGo.
    """

    if DDGS is None:
        return []

    try:

        with DDGS() as ddgs:

            results = list(
                ddgs.text(
                    query,
                    max_results=3
                )
            )

            return [
                f"- [{r['title']}]({r['href']}): {r['body']}"
                for r in results
            ]

    except Exception:

        return []


# ==============================================================================
# 8. SIDEBAR
# ==============================================================================

st.sidebar.title(
    "📍 Smart Local Guide"
)

st.sidebar.markdown(
    "Cloud-powered neighborhood discovery & planning."
)


# API key
user_api_key = st.sidebar.text_input(
    "Google AI Studio API Key",
    type="password",
    help=(
        "Leave blank if GEMINI_API_KEY is already "
        "set in your environment variables."
    )
)


# Model selection
model_choice = st.sidebar.selectbox(
    "Gemini Model",
    [
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]
)


st.sidebar.markdown("---")


# Geofencing
st.sidebar.subheader(
    "⚙️ Domain Guardrails"
)

strict_geofence = st.sidebar.checkbox(
    "Strict 3 km Radius Geofencing",
    value=True
)


# Create client
client = get_gemini_client(
    user_api_key
)


# ==============================================================================
# 9. MAIN TITLE
# ==============================================================================

st.title(
    "🏙️ Smart Local Guide"
)


# ==============================================================================
# 10. TABS
# ==============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🗓️ Itinerary Planner",
        "📌 Places Near You",
        "📝 Area Summarizer",
        "☕ Quiet Work Cafes",
        "🏥 24/7 Medical Care"
    ]
)


# ==============================================================================
# TAB 1 — ITINERARY PLANNER
# ==============================================================================

with tab1:

    st.header(
        "Plan Your Perfect Trip"
    )


    # --------------------------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------------------------

    city = st.text_input(
        "📍 City / Neighborhood",
        "SoHo, New York",
        key="itinerary_city"
    )


    # --------------------------------------------------------------------------
    # DURATION
    # --------------------------------------------------------------------------

    duration = st.selectbox(
        "📅 Duration of Stay",
        [
            "1 Day",
            "2 Days",
            "3 Days",
            "4 Days",
            "5 Days",
            "6 Days",
            "7 Days",
            "1 Week",
            "2 Weeks"
        ],
        key="itinerary_duration"
    )


    # --------------------------------------------------------------------------
    # BUDGET
    # --------------------------------------------------------------------------

    st.subheader(
        "💰 Budget"
    )

    budget = st.slider(
        "Approximate budget per person (₹)",
        min_value=500,
        max_value=100000,
        value=5000,
        step=500,
        key="itinerary_budget"
    )

    st.caption(
        f"Selected budget: ₹{budget:,} per person"
    )


    # --------------------------------------------------------------------------
    # INTERESTS
    # --------------------------------------------------------------------------

    interests = st.multiselect(
        "🎯 Interests",
        [
            "☕ Coffee & Bakery",
            "🎨 Art & Galleries",
            "🛍️ Shopping",
            "🌳 Parks & Nature",
            "🏛️ Historical Sites",
            "🎭 Entertainment & Nightlife",
            "📸 Photography & Scenic Places"
        ],
        default=[
            "☕ Coffee & Bakery",
            "🎨 Art & Galleries"
        ],
        key="itinerary_interests"
    )


    # --------------------------------------------------------------------------
    # EATING PREFERENCE
    # --------------------------------------------------------------------------

    eating_preference = st.multiselect(
        "🍽️ Eating Preference",
        [
            "Indian",
            "Vegetarian",
            "Vegan",
            "Non-Vegetarian",
            "Street Food",
            "Fine Dining",
            "Budget-Friendly Food",
            "Cafes & Bakeries"
        ],
        default=[
            "Budget-Friendly Food"
        ],
        key="itinerary_food"
    )


    # --------------------------------------------------------------------------
    # GROUP TYPE
    # --------------------------------------------------------------------------

    group_type = st.radio(
        "👥 Group Type",
        [
            "Solo",
            "Couple",
            "Family",
            "Friends"
        ],
        horizontal=True,
        key="itinerary_group"
    )


    # --------------------------------------------------------------------------
    # GENERATE ITINERARY
    # --------------------------------------------------------------------------

    if st.button(
        "✨ Generate Itinerary",
        key="btn_itinerary"
    ):

        if not client:

            st.error(
                "Gemini Client not initialized. "
                "Please enter a Google AI Studio API key."
            )

        else:

            with st.spinner(
                "Crafting your customized itinerary..."
            ):

                interests_text = (
                    ", ".join(interests)
                    if interests
                    else "General sightseeing"
                )

                food_text = (
                    ", ".join(eating_preference)
                    if eating_preference
                    else "No specific preference"
                )


                prompt = f"""
Create a detailed travel itinerary.

LOCATION:
{city}

DURATION:
{duration}

BUDGET:
₹{budget:,} per person

GROUP TYPE:
{group_type}

INTERESTS:
{interests_text}

EATING PREFERENCES:
{food_text}

STRICT 3 KM GEOFENCING:
{strict_geofence}

IMPORTANT:

1. Plan the entire trip according to the selected duration.

2. Keep the estimated spending within approximately
   ₹{budget:,} per person.

3. Give estimated prices in Indian Rupees.

4. Break the itinerary into days.

5. For each day include morning, afternoon and evening
   activities where appropriate.

6. Include restaurants and food suggestions based on
   the selected eating preferences.

7. Consider whether the group is solo, couple, family
   or friends.

8. Keep nearby activities grouped together to reduce
   unnecessary travel.

9. If strict geofencing is enabled, prioritize places
   within approximately 3 km of the selected location.

10. Include approximate transportation costs.

11. Include estimated food costs.

12. Include estimated attraction/entry costs where
   applicable.

13. Clearly state when the selected budget may not
   be sufficient.

14. Do not invent exact prices when uncertain.
   Clearly label them as estimates.

15. Make the itinerary easy for a traveler to follow.

Use attractive Markdown headings and bullet points.
"""


                result_text = generate_response(
                    system_prompt=(
                        "You are an expert local travel guide. "
                        "Create realistic, practical and structured "
                        "travel itineraries."
                    ),
                    user_prompt=prompt,
                    model=model_choice
                )


                if result_text:

                    # Save itinerary
                    st.session_state.itinerary_history.append(
                        {
                            "query": (
                                f"{city} • "
                                f"{duration} • "
                                f"₹{budget:,} • "
                                f"{group_type}"
                            ),
                            "content": result_text
                        }
                    )


                    st.markdown(
                        result_text
                    )


                    # Audio
                    audio_data = generate_tts_audio(
                        result_text
                    )

                    if audio_data:

                        st.audio(
                            audio_data,
                            format="audio/mp3"
                        )


                    # PDF
                    pdf_bytes = generate_pdf_bytes(
                        f"Itinerary - {city}",
                        result_text
                    )

                    st.download_button(
                        "📥 Download PDF",
                        data=pdf_bytes,
                        file_name=(
                            f"itinerary_"
                            f"{city.replace(' ', '_')}.pdf"
                        ),
                        mime="application/pdf",
                        key=(
                            f"current_itinerary_pdf_"
                            f"{len(st.session_state.itinerary_history)}"
                        )
                    )


    # ==========================================================================
    # SAVED ITINERARIES
    # ==========================================================================

    st.markdown("---")

    st.subheader(
        f"📚 Saved Itineraries "
        f"({len(st.session_state.itinerary_history)})"
    )


    if st.session_state.itinerary_history:

        if st.button(
            "🗑️ Clear All Itineraries",
            key="clear_itinerary_history"
        ):

            st.session_state.itinerary_history = []

            st.rerun()


        for idx, item in enumerate(
            st.session_state.itinerary_history,
            start=1
        ):

            with st.expander(
                f"🗓️ Itinerary #{idx} — {item['query']}"
            ):

                st.markdown(
                    item["content"]
                )


                pdf_data = generate_pdf_bytes(
                    f"Itinerary #{idx}",
                    item["content"]
                )


                col1, col2 = st.columns(2)


                with col1:

                    st.download_button(
                        "📥 Export PDF",
                        data=pdf_data,
                        file_name=(
                            f"itinerary_{idx}.pdf"
                        ),
                        mime="application/pdf",
                        key=(
                            f"itinerary_download_{idx}"
                        )
                    )


                with col2:

                    if st.button(
                        "🗑️ Delete",
                        key=(
                            f"delete_itinerary_{idx}"
                        )
                    ):

                        st.session_state.itinerary_history.pop(
                            idx - 1
                        )

                        st.rerun()

    else:

        st.info(
            "No itineraries saved yet. "
            "Generate your first itinerary above."
        )


# ==============================================================================
# TAB 2 — PLACES NEAR YOU
# ==============================================================================

with tab2:

    st.header(
        "Discover Nearby Gems"
    )


    loc_input = st.text_input(
        "📍 Your Current Location / Landmark",
        "Eiffel Tower, Paris",
        key="places_location"
    )


    category = st.selectbox(
        "🔎 What are you looking for?",
        [
            "Top Rated Food & Drink",
            "Hotels",
            "Tourist Spots",
            "Shopping",
            "Hospitals",
            "ATMs",
            "Cultural Landmarks",
            "Parks & Nature",
            "Hidden Gems"
        ],
        key="places_category"
    )


    if st.button(
        "🔎 Find Places",
        key="btn_places"
    ):

        if not client:

            st.error(
                "Gemini Client not initialized."
            )

        else:

            with st.spinner(
                "Searching nearby recommendations..."
            ):

                search_results = web_search(
                    f"{category} near {loc_input}"
                )


                search_context = (
                    "\n".join(search_results)
                    if search_results
                    else "No live web snippets found."
                )


                prompt = f"""
Find approximately 5 useful recommendations.

LOCATION:
{loc_input}

CATEGORY:
{category}

RADIUS:
3 km

STRICT GEOFENCING:
{strict_geofence}

WEB SEARCH CONTEXT:
{search_context}

For every recommendation provide:

1. Name
2. Approximate distance
3. Address or area
4. Why it is useful or special
5. Opening hours if available
6. Approximate price level where relevant

Do not pretend uncertain information is verified.
Clearly label estimates.
"""


                result_text = generate_response(
                    system_prompt=(
                        "You are a local concierge. "
                        "Provide useful and factual nearby recommendations."
                    ),
                    user_prompt=prompt,
                    model=model_choice
                )


                if result_text:

                    st.session_state.places_history.append(
                        {
                            "query": (
                                f"{category} near "
                                f"{loc_input}"
                            ),
                            "content": result_text
                        }
                    )


                    st.markdown(
                        result_text
                    )


    # ==========================================================================
    # SAVED PLACES
    # ==========================================================================

    st.markdown("---")

    st.subheader(
        f"📚 Saved Places Searches "
        f"({len(st.session_state.places_history)})"
    )


    if st.session_state.places_history:

        if st.button(
            "🗑️ Clear All Places Searches",
            key="clear_places_history"
        ):

            st.session_state.places_history = []

            st.rerun()


        for idx, item in enumerate(
            st.session_state.places_history,
            start=1
        ):

            with st.expander(
                f"📌 Places Search #{idx} — {item['query']}"
            ):

                st.markdown(
                    item["content"]
                )


                pdf_data = generate_pdf_bytes(
                    f"Places Search #{idx}",
                    item["content"]
                )


                col1, col2 = st.columns(2)


                with col1:

                    st.download_button(
                        "📥 Export PDF",
                        data=pdf_data,
                        file_name=f"places_{idx}.pdf",
                        mime="application/pdf",
                        key=f"places_download_{idx}"
                    )


                with col2:

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_places_{idx}"
                    ):

                        st.session_state.places_history.pop(
                            idx - 1
                        )

                        st.rerun()

    else:

        st.info(
            "No places searches saved yet."
        )


# ==============================================================================
# TAB 3 — AREA SUMMARIZER
# ==============================================================================

with tab3:

    st.header(
        "Get an Area Snapshot"
    )


    neighborhood = st.text_input(
        "Neighborhood or Zip Code",
        "Shoreditch, London",
        key="area_neighborhood"
    )


    if st.button(
        "📝 Summarize Neighborhood",
        key="btn_summarize"
    ):

        if not client:

            st.error(
                "Gemini Client not initialized."
            )

        else:

            with st.spinner(
                "Analyzing neighborhood profile..."
            ):

                prompt = f"""
Provide a comprehensive snapshot of:

{neighborhood}

Include:

- Overall Vibe
- Safety & Walkability
- Public Transit Access
- Food & Nightlife Overview
- Shopping
- Attractions
- Best Time to Visit

Clearly distinguish general information
from uncertain estimates.
"""


                result_text = generate_response(
                    system_prompt=(
                        "You are a neighborhood analyst "
                        "providing structured local overviews."
                    ),
                    user_prompt=prompt,
                    model=model_choice
                )


                if result_text:

                    st.session_state.area_history.append(
                        {
                            "query": neighborhood,
                            "content": result_text
                        }
                    )


                    st.markdown(
                        result_text
                    )


    # ==========================================================================
    # SAVED AREA SUMMARIES
    # ==========================================================================

    st.markdown("---")

    st.subheader(
        f"📚 Saved Area Summaries "
        f"({len(st.session_state.area_history)})"
    )


    if st.session_state.area_history:

        if st.button(
            "🗑️ Clear All Area Summaries",
            key="clear_area_history"
        ):

            st.session_state.area_history = []

            st.rerun()


        for idx, item in enumerate(
            st.session_state.area_history,
            start=1
        ):

            with st.expander(
                f"📝 Area Summary #{idx} — {item['query']}"
            ):

                st.markdown(
                    item["content"]
                )


                pdf_data = generate_pdf_bytes(
                    f"Area Summary #{idx}",
                    item["content"]
                )


                st.download_button(
                    "📥 Export PDF",
                    data=pdf_data,
                    file_name=(
                        f"area_summary_{idx}.pdf"
                    ),
                    mime="application/pdf",
                    key=f"area_download_{idx}"
                )

    else:

        st.info(
            "No area summaries saved yet."
        )


# ==============================================================================
# TAB 4 — QUIET WORK CAFES
# ==============================================================================

with tab4:

    st.header(
        "Find Quiet Work & Study Spots"
    )


    cafe_loc = st.text_input(
        "📍 Location",
        "Downtown Seattle",
        key="cafe_loc"
    )


    amenities = st.multiselect(
        "Required Amenities",
        [
            "Fast Wi-Fi",
            "Power Outlets",
            "Quiet Atmosphere",
            "Good Coffee",
            "Spacious Seating"
        ],
        default=[
            "Fast Wi-Fi",
            "Power Outlets"
        ],
        key="cafe_amenities"
    )


    if st.button(
        "☕ Find Cafes",
        key="btn_cafes"
    ):

        if not client:

            st.error(
                "Gemini Client not initialized."
            )

        else:

            with st.spinner(
                "Locating optimal work spots..."
            ):

                prompt = f"""
Recommend 3-4 laptop-friendly cafes in:

{cafe_loc}

Required amenities:

{', '.join(amenities)}

Strict 3 km proximity:

{strict_geofence}

For every cafe include:

- Name
- Approximate distance
- Wi-Fi
- Power outlets
- Noise level
- Seating
- Coffee quality
- Useful study/work information

Clearly label uncertain information.
"""


                result_text = generate_response(
                    system_prompt=(
                        "You are a remote worker assistant "
                        "specializing in finding laptop-friendly spots."
                    ),
                    user_prompt=prompt,
                    model=model_choice
                )


                if result_text:

                    st.session_state.cafe_history.append(
                        {
                            "query": cafe_loc,
                            "content": result_text
                        }
                    )


                    st.markdown(
                        result_text
                    )


    # ==========================================================================
    # SAVED CAFE SEARCHES
    # ==========================================================================

    st.markdown("---")

    st.subheader(
        f"📚 Saved Cafe Searches "
        f"({len(st.session_state.cafe_history)})"
    )


    if st.session_state.cafe_history:

        if st.button(
            "🗑️ Clear All Cafe Searches",
            key="clear_cafe_history"
        ):

            st.session_state.cafe_history = []

            st.rerun()


        for idx, item in enumerate(
            st.session_state.cafe_history,
            start=1
        ):

            with st.expander(
                f"☕ Cafe Search #{idx} — {item['query']}"
            ):

                st.markdown(
                    item["content"]
                )


                pdf_data = generate_pdf_bytes(
                    f"Cafe Search #{idx}",
                    item["content"]
                )


                st.download_button(
                    "📥 Export PDF",
                    data=pdf_data,
                    file_name=f"cafes_{idx}.pdf",
                    mime="application/pdf",
                    key=f"cafe_download_{idx}"
                )

    else:

        st.info(
            "No cafe searches saved yet."
        )


# ==============================================================================
# TAB 5 — MEDICAL CARE
# ==============================================================================

with tab5:

    st.header(
        "Emergency & Urgent Care Search"
    )


    med_loc = st.text_input(
        "📍 Your Emergency Location",
        "Central Station, Berlin",
        key="med_location"
    )


    care_type = st.radio(
        "Type of Care Needed",
        [
            "24/7 Hospital / ER",
            "Urgent Care Clinic",
            "Late Night Pharmacy"
        ],
        key="medical_type"
    )


    if st.button(
        "🏥 Find Nearest Care",
        key="btn_med"
    ):

        if not client:

            st.error(
                "Gemini Client not initialized."
            )

        else:

            with st.spinner(
                "Locating medical facilities..."
            ):

                search_results = web_search(
                    f"{care_type} near {med_loc}"
                )


                search_context = (
                    "\n".join(search_results)
                    if search_results
                    else ""
                )


                prompt = f"""
Find the nearest verified:

{care_type}

near:

{med_loc}

SEARCH RADIUS:
3 km

STRICT GEOFENCING:
{strict_geofence}

WEB SEARCH CONTEXT:

{search_context}

Provide:

- Facility name
- Approximate distance
- Address
- Opening status if available
- Phone number if available
- Emergency contact information if applicable

Do not invent emergency numbers or opening hours.

If information cannot be verified,
clearly say so.
"""


                result_text = generate_response(
                    system_prompt=(
                        "You are an urgent assistance system. "
                        "Provide clean and factual information. "
                        "For emergencies, tell users to contact "
                        "their local emergency services immediately."
                    ),
                    user_prompt=prompt,
                    model=model_choice
                )


                if result_text:

                    st.session_state.medical_history.append(
                        {
                            "query": (
                                f"{care_type} - "
                                f"{med_loc}"
                            ),
                            "content": result_text
                        }
                    )


                    st.markdown(
                        result_text
                    )


    # ==========================================================================
    # SAVED MEDICAL SEARCHES
    # ==========================================================================

    st.markdown("---")

    st.subheader(
        f"📚 Saved Medical Searches "
        f"({len(st.session_state.medical_history)})"
    )


    if st.session_state.medical_history:

        if st.button(
            "🗑️ Clear All Medical Searches",
            key="clear_medical_history"
        ):

            st.session_state.medical_history = []

            st.rerun()


        for idx, item in enumerate(
            st.session_state.medical_history,
            start=1
        ):

            with st.expander(
                f"🏥 Medical Search #{idx} — {item['query']}"
            ):

                st.markdown(
                    item["content"]
                )


                pdf_data = generate_pdf_bytes(
                    f"Medical Search #{idx}",
                    item["content"]
                )


                st.download_button(
                    "📥 Export PDF",
                    data=pdf_data,
                    file_name=f"medical_{idx}.pdf",
                    mime="application/pdf",
                    key=f"medical_download_{idx}"
                )

    else:

        st.info(
            "No medical searches saved yet."
        )