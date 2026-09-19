import os
import io
import time
import streamlit as st

from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF
from gtts import gTTS

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# OPTIONAL DUCKDUCKGO IMPORT
# ============================================================

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart Local Guide",
    page_icon="🧭",
    layout="wide"
)


# ============================================================
# THEMES
# ============================================================

THEMES = {
    "Warm Aesthetic": {
        "background": "#FFF8F0",
        "text": "#3D2B1F",
        "primary": "#C76B3C",
        "secondary": "#F2D4C4"
    },
    "Rose Gold": {
        "background": "#FFF5F7",
        "text": "#4A3038",
        "primary": "#B76E79",
        "secondary": "#F3D6DC"
    },
    "Sage Green": {
        "background": "#F4F8F1",
        "text": "#304332",
        "primary": "#718C70",
        "secondary": "#DCE8D8"
    },
    "Classic Light": {
        "background": "#FFFFFF",
        "text": "#222222",
        "primary": "#4F6D8A",
        "secondary": "#E8EEF3"
    }
}


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🧭 Smart Local Guide")

theme_choice = st.sidebar.selectbox(
    "Choose Theme",
    list(THEMES.keys())
)

theme = THEMES[theme_choice]

st.sidebar.markdown("---")

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

strict_radius = st.sidebar.checkbox(
    "Strict 3 km radius",
    value=False
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {theme["background"]};
        color: {theme["text"]};
    }}

    h1, h2, h3 {{
        color: {theme["text"]};
    }}

    .stButton > button {{
        background-color: {theme["primary"]};
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
    }}

    .stButton > button:hover {{
        background-color: {theme["primary"]};
        color: white;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION STATE - SEPARATE HISTORIES
# ============================================================

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


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_gemini_client():
    """
    Gets Gemini API key from environment variables.

    Locally:
        .env file

    Render:
        Environment Variable
        GEMINI_API_KEY
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error(
            "Gemini API key is not configured. "
            "Please set the GEMINI_API_KEY environment variable."
        )
        return None

    return OpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )


# ============================================================
# GEMINI RESPONSE WITH RETRY / FALLBACK
# ============================================================

def generate_response(system_prompt, user_prompt, model):

    client = get_gemini_client()

    if not client:
        return None

    fallback_models = [
        model,
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite"
    ]

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

                if "503" in error_text or "UNAVAILABLE" in error_text:

                    if attempt == 0:
                        time.sleep(2)
                        continue

                    break

                raise e

    st.error(
        "⚠️ Gemini is temporarily unavailable. "
        "Please try again in a few moments."
    )

    if last_error:
        st.caption(f"Last error: {last_error}")

    return None


# ============================================================
# TEXT TO SPEECH
# ============================================================

def generate_tts_audio(text):

    try:

        audio_buffer = io.BytesIO()

        tts = gTTS(
            text=text,
            lang="en"
        )

        tts.write_to_fp(audio_buffer)

        audio_buffer.seek(0)

        return audio_buffer

    except Exception as e:

        st.error(f"TTS error: {e}")

        return None


# ============================================================
# PDF GENERATION
# ============================================================

def generate_pdf_bytes(title, content):

    pdf = FPDF()

    pdf.add_page()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.multi_cell(
        0,
        10,
        title
    )

    pdf.ln(5)

    pdf.set_font(
        "Arial",
        size=11
    )

    clean_content = content.encode(
        "latin-1",
        "replace"
    ).decode("latin-1")

    pdf.multi_cell(
        0,
        7,
        clean_content
    )

    return bytes(pdf.output())


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(query, max_results=6):

    if DDGS is None:
        return "Web search package is not installed."

    results = []

    try:

        with DDGS() as ddgs:

            search_results = ddgs.text(
                query,
                max_results=max_results
            )

            for result in search_results:

                title = result.get(
                    "title",
                    ""
                )

                body = result.get(
                    "body",
                    ""
                )

                href = result.get(
                    "href",
                    ""
                )

                results.append(
                    f"Title: {title}\n"
                    f"Description: {body}\n"
                    f"URL: {href}"
                )

    except Exception as e:

        return f"Web search unavailable: {e}"

    if not results:
        return "No useful web-search results were found."

    return "\n\n".join(results)


# ============================================================
# TITLE
# ============================================================

st.title("🧭 Smart Local Guide")

st.write(
    "Your AI-powered assistant for travel planning, "
    "local discovery, neighborhoods, cafes and medical services."
)


# ============================================================
# TABS
# ============================================================

tabs = st.tabs(
    [
        "🗺️ Itinerary Planner",
        "📍 Places Near You",
        "🏙️ Area Summarizer",
        "☕ Quiet Work Cafes",
        "🏥 24/7 Medical Care"
    ]
)


# ============================================================
# TAB 1 - ITINERARY PLANNER
# ============================================================

with tabs[0]:

    st.header("🗺️ Itinerary Planner")

    city = st.text_input(
        "City / Neighborhood",
        placeholder="e.g. Connaught Place, Delhi"
    )

    duration = st.selectbox(
        "Duration of Stay",
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
        ]
    )

    budget = st.slider(
        "Approximate budget per person (₹)",
        min_value=500,
        max_value=100000,
        value=5000,
        step=500
    )

    interests = st.multiselect(
        "Interests",
        [
            "Coffee & Bakery",
            "Art & Galleries",
            "Shopping",
            "Parks & Nature",
            "Historical Sites",
            "Entertainment & Nightlife",
            "Photography & Scenic Places"
        ]
    )

    eating_preference = st.multiselect(
        "Eating Preference",
        [
            "Indian",
            "Vegetarian",
            "Vegan",
            "Non-Vegetarian",
            "Street Food",
            "Fine Dining",
            "Budget-Friendly Food",
            "Cafes & Bakeries"
        ]
    )

    group_type = st.selectbox(
        "Group Type",
        [
            "Solo",
            "Couple",
            "Family",
            "Friends"
        ]
    )

    if st.button(
        "✨ Generate Itinerary",
        key="generate_itinerary"
    ):

        if not city.strip():

            st.warning(
                "Please enter a city or neighborhood."
            )

        else:

            radius_instruction = ""

            if strict_radius:

                radius_instruction = """
                Prefer activities and places within approximately
                3 km of the selected location whenever possible.
                """

            system_prompt = """
            You are a helpful travel planning assistant.
            Create practical, realistic and well-organized
            travel itineraries.
            """

            user_prompt = f"""
            Create a travel itinerary for:

            Location:
            {city}

            Duration:
            {duration}

            Approximate budget per person:
            ₹{budget}

            Interests:
            {", ".join(interests) if interests else "General sightseeing"}

            Eating preferences:
            {", ".join(eating_preference) if eating_preference else "Flexible"}

            Group type:
            {group_type}

            {radius_instruction}

            Requirements:

            1. Break the itinerary down by day.
            2. Include morning, afternoon and evening activities.
            3. Include food suggestions based on eating preferences.
            4. Consider the selected group type.
            5. Keep estimated spending around the selected budget.
            6. Show estimated costs in Indian Rupees.
            7. Include transportation costs where useful.
            8. Include entry fees where applicable.
            9. Group nearby activities together when possible.
            10. Clearly mention that prices and availability are estimates.
            11. If the budget may not be sufficient, explain why.
            12. Keep the itinerary practical and easy to follow.
            """

            result = generate_response(
                system_prompt,
                user_prompt,
                model_choice
            )

            if result:

                st.session_state.itinerary_history.append(
                    {
                        "location": city,
                        "duration": duration,
                        "budget": budget,
                        "result": result
                    }
                )

                st.success(
                    "Itinerary generated successfully!"
                )

                st.markdown(result)

                # TTS
                audio = generate_tts_audio(result)

                if audio:

                    st.audio(
                        audio,
                        format="audio/mp3"
                    )

                # PDF
                pdf_bytes = generate_pdf_bytes(
                    f"Itinerary - {city}",
                    result
                )

                st.download_button(
                    "📄 Download Itinerary PDF",
                    data=pdf_bytes,
                    file_name="smart_local_guide_itinerary.pdf",
                    mime="application/pdf"
                )

    # ========================================================
    # SAVED ITINERARIES
    # ========================================================

    if st.session_state.itinerary_history:

        st.markdown("---")

        st.subheader("💾 Saved Itineraries")

        for index, item in enumerate(
            reversed(st.session_state.itinerary_history)
        ):

            actual_index = (
                len(st.session_state.itinerary_history)
                - 1
                - index
            )

            with st.expander(
                f"Itinerary #{actual_index + 1} - {item['location']}"
            ):

                st.write(
                    f"**Duration:** {item['duration']}"
                )

                st.write(
                    f"**Budget:** ₹{item['budget']}"
                )

                st.markdown(
                    item["result"]
                )

                col1, col2 = st.columns(2)

                with col1:

                    pdf_bytes = generate_pdf_bytes(
                        f"Itinerary - {item['location']}",
                        item["result"]
                    )

                    st.download_button(
                        "📄 PDF",
                        data=pdf_bytes,
                        file_name=f"itinerary_{actual_index + 1}.pdf",
                        mime="application/pdf",
                        key=f"itinerary_pdf_{actual_index}"
                    )

                with col2:

                    if st.button(
                        "🗑️ Delete",
                        key=f"delete_itinerary_{actual_index}"
                    ):

                        st.session_state.itinerary_history.pop(
                            actual_index
                        )

                        st.rerun()

        if st.button(
            "🗑️ Clear Itinerary History"
        ):

            st.session_state.itinerary_history = []

            st.rerun()


# ============================================================
# TAB 2 - PLACES NEAR YOU
# ============================================================

with tabs[1]:

    st.header("📍 Places Near You")

    place_location = st.text_input(
        "Location",
        placeholder="e.g. Connaught Place, Delhi",
        key="place_location"
    )

    place_category = st.selectbox(
        "Category",
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
        ]
    )

    if st.button(
        "🔎 Find Places",
        key="find_places"
    ):

        if not place_location.strip():

            st.warning(
                "Please enter a location."
            )

        else:

            search_query = (
                f"{place_category} near "
                f"{place_location}"
            )

            search_context = web_search(
                search_query
            )

            radius_instruction = ""

            if strict_radius:

                radius_instruction = """
                Prefer results within approximately
                3 km of the specified location.
                """

            system_prompt = """
            You are a local discovery assistant.
            Use the supplied search information carefully.
            Do not invent facts when information is unavailable.
            """

            user_prompt = f"""
            Find and organize useful recommendations for:

            Location:
            {place_location}

            Category:
            {place_category}

            {radius_instruction}

            Web search context:
            {search_context}

            Give approximately 5 useful recommendations.

            For each recommendation include:

            - Name
            - Location or distance if available
            - Address or area
            - Why it is useful
            - Opening hours if available
            - Price level if available

            Clearly identify information that could not be verified.
            """

            result = generate_response(
                system_prompt,
                user_prompt,
                model_choice
            )

            if result:

                st.session_state.places_history.append(
                    {
                        "location": place_location,
                        "category": place_category,
                        "result": result
                    }
                )

                st.success(
                    "Places found successfully!"
                )

                st.markdown(result)

    # ========================================================
    # SAVED PLACES
    # ========================================================

    if st.session_state.places_history:

        st.markdown("---")

        st.subheader("💾 Saved Place Searches")

        for index, item in enumerate(
            reversed(st.session_state.places_history)
        ):

            actual_index = (
                len(st.session_state.places_history)
                - 1
                - index
            )

            with st.expander(
                f"Search #{actual_index + 1} - "
                f"{item['location']} - "
                f"{item['category']}"
            ):

                st.markdown(
                    item["result"]
                )

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_place_{actual_index}"
                ):

                    st.session_state.places_history.pop(
                        actual_index
                    )

                    st.rerun()

        if st.button(
            "🗑️ Clear Places History"
        ):

            st.session_state.places_history = []

            st.rerun()


# ============================================================
# TAB 3 - AREA SUMMARIZER
# ============================================================

with tabs[2]:

    st.header("🏙️ Area / Neighborhood Summarizer")

    area_location = st.text_input(
        "Neighborhood / ZIP / Postal Code",
        placeholder="e.g. 110001 or Connaught Place",
        key="area_location"
    )

    if st.button(
        "🏙️ Summarize Area",
        key="summarize_area"
    ):

        if not area_location.strip():

            st.warning(
                "Please enter an area."
            )

        else:

            system_prompt = """
            You are an area and neighborhood analysis assistant.
            Provide practical and balanced information.
            """

            user_prompt = f"""
            Give an overview of:

            {area_location}

            Discuss:

            - Restaurants
            - Cafes
            - ATMs
            - Hospitals
            - Attractions
            - Shopping
            - General character of the area
            - Useful facilities
            - Potential advantages
            - Potential disadvantages

            Keep the explanation practical.
            Clearly identify information that may need verification.
            """

            result = generate_response(
                system_prompt,
                user_prompt,
                model_choice
            )

            if result:

                st.session_state.area_history.append(
                    {
                        "location": area_location,
                        "result": result
                    }
                )

                st.success(
                    "Area summary generated!"
                )

                st.markdown(result)

    # ========================================================
    # SAVED AREA SUMMARIES
    # ========================================================

    if st.session_state.area_history:

        st.markdown("---")

        st.subheader("💾 Saved Area Summaries")

        for index, item in enumerate(
            reversed(st.session_state.area_history)
        ):

            actual_index = (
                len(st.session_state.area_history)
                - 1
                - index
            )

            with st.expander(
                f"Summary #{actual_index + 1} - "
                f"{item['location']}"
            ):

                st.markdown(
                    item["result"]
                )

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_area_{actual_index}"
                ):

                    st.session_state.area_history.pop(
                        actual_index
                    )

                    st.rerun()

        if st.button(
            "🗑️ Clear Area History"
        ):

            st.session_state.area_history = []

            st.rerun()


# ============================================================
# TAB 4 - QUIET WORK CAFES
# ============================================================

with tabs[3]:

    st.header("☕ Quiet Work Cafes")

    cafe_location = st.text_input(
        "Location",
        placeholder="e.g. South Delhi",
        key="cafe_location"
    )

    cafe_amenities = st.multiselect(
        "Preferred Amenities",
        [
            "Wi-Fi",
            "Power outlets",
            "Quiet environment",
            "Air conditioning",
            "Long seating",
            "Good coffee",
            "Food availability"
        ]
    )

    if st.button(
        "☕ Find Work Cafes",
        key="find_cafes"
    ):

        if not cafe_location.strip():

            st.warning(
                "Please enter a location."
            )

        else:

            system_prompt = """
            You are a cafe recommendation assistant.
            """

            user_prompt = f"""
            Recommend quiet work-friendly cafes around:

            Location:
            {cafe_location}

            Preferred amenities:
            {", ".join(cafe_amenities)
            if cafe_amenities
            else "General work-friendly amenities"}

            Provide useful recommendations.

            Mention:
            - Cafe name
            - Location
            - Why it may be suitable for work
            - Amenities
            - Price level if available
            - Any useful practical information

            Do not invent information.
            Clearly mention uncertainty where appropriate.
            """

            result = generate_response(
                system_prompt,
                user_prompt,
                model_choice
            )

            if result:

                st.session_state.cafe_history.append(
                    {
                        "location": cafe_location,
                        "amenities": cafe_amenities,
                        "result": result
                    }
                )

                st.success(
                    "Cafe recommendations generated!"
                )

                st.markdown(result)

    # ========================================================
    # SAVED CAFES
    # ========================================================

    if st.session_state.cafe_history:

        st.markdown("---")

        st.subheader("💾 Saved Cafe Searches")

        for index, item in enumerate(
            reversed(st.session_state.cafe_history)
        ):

            actual_index = (
                len(st.session_state.cafe_history)
                - 1
                - index
            )

            with st.expander(
                f"Search #{actual_index + 1} - "
                f"{item['location']}"
            ):

                st.markdown(
                    item["result"]
                )

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_cafe_{actual_index}"
                ):

                    st.session_state.cafe_history.pop(
                        actual_index
                    )

                    st.rerun()

        if st.button(
            "🗑️ Clear Cafe History"
        ):

            st.session_state.cafe_history = []

            st.rerun()


# ============================================================
# TAB 5 - MEDICAL CARE
# ============================================================

with tabs[4]:

    st.header("🏥 24/7 Medical Care")

    medical_location = st.text_input(
        "Location",
        placeholder="e.g. Noida Sector 18",
        key="medical_location"
    )

    medical_type = st.selectbox(
        "Medical Service",
        [
            "24/7 Hospital / Emergency Room",
            "Urgent Care",
            "Late Night Pharmacy"
        ]
    )

    if st.button(
        "🏥 Find Medical Services",
        key="find_medical"
    ):

        if not medical_location.strip():

            st.warning(
                "Please enter a location."
            )

        else:

            search_query = (
                f"{medical_type} near "
                f"{medical_location}"
            )

            search_context = web_search(
                search_query
            )

            radius_instruction = ""

            if strict_radius:

                radius_instruction = """
                Prefer results within approximately
                3 km of the specified location.
                """

            system_prompt = """
            You are a medical-location information assistant.
            Accuracy and uncertainty are important.
            """

            user_prompt = f"""
            Find useful medical services around:

            Location:
            {medical_location}

            Service:
            {medical_type}

            {radius_instruction}

            Search context:
            {search_context}

            Provide:

            - Name
            - Location/address
            - Available service
            - Opening or availability information if found
            - Contact information if available
            - Other useful details

            Clearly state when information could not be verified.

            Do not claim that a medical facility is currently
            open or available unless the information supports it.
            """

            result = generate_response(
                system_prompt,
                user_prompt,
                model_choice
            )

            if result:

                st.session_state.medical_history.append(
                    {
                        "location": medical_location,
                        "type": medical_type,
                        "result": result
                    }
                )

                st.warning(
                    "For emergencies, always contact "
                    "local emergency services or the "
                    "medical facility directly."
                )

                st.markdown(result)

    # ========================================================
    # SAVED MEDICAL SEARCHES
    # ========================================================

    if st.session_state.medical_history:

        st.markdown("---")

        st.subheader("💾 Saved Medical Searches")

        for index, item in enumerate(
            reversed(st.session_state.medical_history)
        ):

            actual_index = (
                len(st.session_state.medical_history)
                - 1
                - index
            )

            with st.expander(
                f"Search #{actual_index + 1} - "
                f"{item['location']} - "
                f"{item['type']}"
            ):

                st.markdown(
                    item["result"]
                )

                if st.button(
                    "🗑️ Delete",
                    key=f"delete_medical_{actual_index}"
                ):

                    st.session_state.medical_history.pop(
                        actual_index
                    )

                    st.rerun()

        if st.button(
            "🗑️ Clear Medical History"
        ):

            st.session_state.medical_history = []

            st.rerun()