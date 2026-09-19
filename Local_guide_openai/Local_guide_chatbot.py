import os
import io
import json
import streamlit as st
import requests
from openai import OpenAI
from fpdf import FPDF
from gtts import gTTS

# Try importing DuckDuckGo search library safely
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        DDGS = None

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

# Sidebar Theme Selector
selected_theme = st.sidebar.selectbox("🎨 Choose Theme", list(THEMES.keys()), index=0)
theme_colors = THEMES[selected_theme]

# Apply Dynamic CSS Styling
st.markdown(f"""
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
""", unsafe_allow_html=True)

# Initialize Session State Variables
if "history" not in st.session_state:
    st.session_state.history = []

# ==============================================================================
# 2. HELPER FUNCTIONS (API Calls, TTS, Export)
# ==============================================================================

def get_openai_client(user_api_key=""):
    """Get OpenAI Client using environment variable or user-provided key."""
    api_key = os.environ.get("OPENAI_API_KEY") or user_api_key
    if not api_key:
        st.sidebar.error("⚠️ Please provide an OpenAI API Key in the sidebar or environment variables.")
        return None
    return OpenAI(api_key=api_key)

def generate_tts_audio(text):
    """Generate audio using gTTS for cloud deployment compatibility."""
    try:
        clean_text = text.replace("*", "").replace("#", "").replace("-", "")[:400]
        tts = gTTS(text=clean_text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        return fp.read()
    except Exception as e:
        st.warning(f"Audio generation failed: {e}")
        return None

def generate_pdf_bytes(title, content):
    """Generate a simple PDF document using fpdf2."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=16, style="B")
    pdf.cell(200, 10, txt=title, ln=1, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", size=10)
    
    # Handle simple text encoding
    clean_content = content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, txt=clean_content)
    
    return bytes(pdf.output())

def web_search(query):
    """Perform a web search using DuckDuckGo."""
    if DDGS is None:
        return []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            return [f"- [{r['title']}]({r['href']}): {r['body']}" for r in results]
    except Exception:
        return []

# ==============================================================================
# 3. SIDEBAR CONFIGURATION
# ==============================================================================
st.sidebar.title("📍 Smart Local Guide")
st.sidebar.markdown("Cloud-powered neighborhood discovery & planning.")

user_api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Leave blank if set in environment variables.")
model_choice = st.sidebar.selectbox("Model", ["gpt-4o-mini", "gpt-4o"])

st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Domain Guardrails")
strict_geofence = st.sidebar.checkbox("Strict 3 km Radius Geofencing", value=True)

# Initialize OpenAI Client
client = get_openai_client(user_api_key)

# ==============================================================================
# 4. MAIN INTERFACE & TABBED NAVIGATION
# ==============================================================================
st.title("🏙️ Smart Local Guide")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗓️ Itinerary Planner", 
    "📌 Places Near You", 
    "📝 Area Summarizer", 
    "☕ Quiet Work Cafes", 
    "🏥 24/7 Medical Care",
    "📜 History"
])

# ------------------------------------------------------------------------------
# TAB 1: ITINERARY PLANNER
# ------------------------------------------------------------------------------
with tab1:
    st.header("Plan Your Perfect Day")
    col1, col2 = st.columns(2)
    with col1:
        city = st.text_input("City / Neighborhood", "SoHo, New York")
        duration = st.selectbox("Duration", ["Half Day (4 hours)", "Full Day (8 hours)", "Weekend (2 days)"])
    with col2:
        interests = st.multiselect("Interests", ["Coffee & Bakery", "Art & Galleries", "Shopping", "Parks", "Historical Sites"], default=["Coffee & Bakery", "Art & Galleries"])
        pace = st.select_slider("Pace", options=["Relaxed", "Balanced", "Fast-paced"])
        
    if st.button("Generate Itinerary", key="btn_itinerary"):
        if not client:
            st.error("OpenAI Client not initialized. Please enter an API key.")
        else:
            with st.spinner("Crafting customized itinerary..."):
                prompt = f"Create a detailed, highly local itinerary for {city}. Duration: {duration}. Interests: {', '.join(interests)}. Pace: {pace}. Strict geofencing within 3 km radius: {strict_geofence}."
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "You are an expert local guide providing structured, beautiful markdown itineraries."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                st.markdown(result_text)
                
                # Save to History
                st.session_state.history.append({"type": "Itinerary", "query": f"{city} - {duration}", "content": result_text})
                
                # Audio & Download Options
                audio_data = generate_tts_audio(result_text)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3")
                    
                pdf_bytes = generate_pdf_bytes(f"Itinerary - {city}", result_text)
                st.download_button("📥 Download PDF", data=pdf_bytes, file_name=f"itinerary_{city}.pdf", mime="application/pdf")

# ------------------------------------------------------------------------------
# TAB 2: PLACES NEAR YOU
# ------------------------------------------------------------------------------
with tab2:
    st.header("Discover Nearby Gems")
    loc_input = st.text_input("Your Current Location / Landmark", "Eiffel Tower, Paris")
    category = st.selectbox("Category", ["Top Rated Food & Drink", "Hidden Gems", "Cultural Landmarks", "Parks & Nature"])
    
    if st.button("Find Places", key="btn_places"):
        if not client:
            st.error("OpenAI Client not initialized.")
        else:
            with st.spinner("Searching nearby recommendations..."):
                search_results = web_search(f"{category} near {loc_input}")
                search_context = "\n".join(search_results) if search_results else "No live web snippets found."
                
                prompt = f"List 5 top recommendations for '{category}' within 3 km of {loc_input}.\nWeb context:\n{search_context}"
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "You are a local concierge. Return numbered items with distance estimates, address/area, and why it's special."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                st.markdown(result_text)
                
                st.session_state.history.append({"type": "Places Near You", "query": f"{category} near {loc_input}", "content": result_text})

# ------------------------------------------------------------------------------
# TAB 3: AREA SUMMARIZER
# ------------------------------------------------------------------------------
with tab3:
    st.header("Get an Area Snapshot")
    neighborhood = st.text_input("Neighborhood or Zip Code", "Shoreditch, London")
    
    if st.button("Summarize Neighborhood", key="btn_summarize"):
        if not client:
            st.error("OpenAI Client not initialized.")
        else:
            with st.spinner("Analyzing neighborhood profile..."):
                prompt = f"Provide a comprehensive snapshot of {neighborhood}. Include: Overall Vibe, Safety & Walkability, Public Transit Access, Food & Nightlife Overview, and Best Time to Visit."
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "You are a neighborhood analyst providing structured local overviews."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                st.markdown(result_text)
                st.session_state.history.append({"type": "Area Summary", "query": neighborhood, "content": result_text})

# ------------------------------------------------------------------------------
# TAB 4: QUIET WORK CAFES
# ------------------------------------------------------------------------------
with tab4:
    st.header("Find Quiet Work & Study Spots")
    cafe_loc = st.text_input("Location", "Downtown Seattle", key="cafe_loc")
    amenities = st.multiselect("Required Amenities", ["Fast Wi-Fi", "Power Outlets", "Quiet Atmosphere", "Good Coffee", "Spacious Seating"], default=["Fast Wi-Fi", "Power Outlets"])
    
    if st.button("Find Cafes", key="btn_cafes"):
        if not client:
            st.error("OpenAI Client not initialized.")
        else:
            with st.spinner("Locating optimal work spots..."):
                prompt = f"Recommend 3-4 laptop-friendly cafes in {cafe_loc} with amenities: {', '.join(amenities)}. Enforce strict 3km proximity."
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "You are a remote worker assistant specializing in finding laptop-friendly spots."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                st.markdown(result_text)
                st.session_state.history.append({"type": "Quiet Cafes", "query": cafe_loc, "content": result_text})

# ------------------------------------------------------------------------------
# TAB 5: 24/7 MEDICAL CARE
# ------------------------------------------------------------------------------
with tab5:
    st.header("Emergency & Urgent Care Search")
    med_loc = st.text_input("Your Emergency Location", "Central Station, Berlin")
    care_type = st.radio("Type of Care Needed", ["24/7 Hospital / ER", "Urgent Care Clinic", "Late Night Pharmacy"])
    
    if st.button("Find Nearest Care", key="btn_med"):
        if not client:
            st.error("OpenAI Client not initialized.")
        else:
            with st.spinner("Locating medical facilities..."):
                search_results = web_search(f"{care_type} near {med_loc}")
                search_context = "\n".join(search_results) if search_results else ""
                
                prompt = f"Find the nearest verified {care_type} within 3 km of {med_loc}. Provide emergency hotline info if applicable.\nContext:\n{search_context}"
                
                response = client.chat.completions.create(
                    model=model_choice,
                    messages=[
                        {"role": "system", "content": "You are an urgent assistance system. Provide immediate, clean, factual information with emergency contacts clearly emphasized."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                result_text = response.choices[0].message.content
                st.markdown(result_text)
                st.session_state.history.append({"type": "Medical Care", "query": f"{care_type} - {med_loc}", "content": result_text})

# ------------------------------------------------------------------------------
# TAB 6: HISTORY & INDIVIDUAL DELETION
# ------------------------------------------------------------------------------
with tab6:
    st.header("Saved Searches & Itineraries")
    if not st.session_state.history:
        st.info("No saved history yet. Generate an itinerary or search for places to populate history.")
    else:
        for idx, item in enumerate(st.session_state.history):
            with st.expander(f"#{idx + 1} [{item['type']}] - {item['query']}"):
                st.markdown(item["content"])
                
                col_del, col_down = st.columns([1, 4])
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{idx}"):
                        st.session_state.history.pop(idx)
                        st.rerun()
                with col_down:
                    pdf_data = generate_pdf_bytes(f"{item['type']} - {item['query']}", item["content"])
                    st.download_button("📥 Export PDF", data=pdf_data, file_name=f"export_{idx+1}.pdf", mime="application/pdf", key=f"dl_{idx}")