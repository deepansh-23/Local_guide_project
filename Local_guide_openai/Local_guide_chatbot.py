import streamlit as st
import requests
import math
import time
import io
import re
import json
import pyttsx3
import pythoncom
import speech_recognition as sr
from datetime import datetime
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions

# Initialize local ChromaDB vector store
chroma_client = chromadb.Client()
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Create or get collection
dataset_collection = chroma_client.get_or_create_collection(
    name="local_venue_data",
    embedding_function=sentence_transformer_ef
)

def load_dataset_into_vectorstore(csv_file_path=r"C:\Users\saumy\OneDrive\Desktop\AI itc101\ollama_chatbot\datasets\zomato_restaurants_in_India.csv"):
    """Loads a CSV dataset and converts venue details into vector embeddings."""
    try:
        df = pd.read_csv(csv_file_path)
        documents = []
        metadatas = []
        ids = []
        return True
    except Exception as e:
        print("[Dataset Error]",e)
        return False

        for idx, row in df.iterrows():
            name = str(row.get("name", "Unknown"))
            locality = str(row.get("locality", "Unknown"))
            city=str(row.get("city","Unknown"))                 
            cuisines = str(row.get("cuisines", "N/A"))
            cost = str(row.get("cost_for_two", "N/A"))
            rating = str(row.get("aggregate_rating", "N/A"))

            # Construct text representation for vector indexing
            text_doc = f"Name: {name} | Locality: {locality} | Cuisines: {cuisines} | Cost for Two: ₹{cost} | Popular Dishes: {dishes}"
            
            documents.append(text_doc)
            metadatas.append({"name": name, "locality": locality, "cost_for_two": cost})
            ids.append(f"venue_{idx}")

        dataset_collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return True
    except Exception as e:
        print("[Dataset Error]", e)
        return False



OLLAMA_URL = "http://localhost:11434/api/chat"

# Optional: You can set fallback default keys here
DEFAULT_GEOAPIFY_KEY = ""
DEFAULT_FOURSQUARE_KEY = ""

# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = (
    "You are a smart local guide assistant. You reason over live places, weather, venue ratings, "
    "and local menu datasets.\n\n"
    "DISTANCE & LOCATION RULES:\n"
    "1. Do NOT calculate or include distances, travel times, or walk/drive estimates unless the user explicitly asks "
    "for 'nearby' places, requests distances, or specifies a current location/landmark to measure from.\n"
    "2. For general queries (e.g., requests for lists, recommendations, budget options, or area overviews without explicit location context):\n"
    "   - Always include the venue's Locality/City (e.g., 'Connaught Place, New Delhi') instead of distance.\n"
    "   - Do NOT reference LIVE SYSTEM TIME for distance calculations unless specifically asked for an itinerary or time-based plan.\n"
    "3. At the end of every listing response where distances are omitted, append this exact prompt:\n"
    "   '💡 Would you like to check distances to any of these places? If so, please enter your location in the sidebar or ask for distance calculations!'\n\n"
    "FEATURE 3 - AREA / NEIGHBORHOOD SUMMARIZER:\n"
    "When asked about an area, landmark, college, or neighborhood, determine its character "
    "from the mix of amenities. Gather multiple amenity categories before answering: restaurants, "
    "cafes, ATMs, hospitals, tourist attractions, and parks. Mention useful strengths, venue ratings, "
    "locality info, and limitations.\n\n"
    "FEATURE 4 - PERSONALIZED ITINERARY PLANNER:\n"
    "1. Do NOT default only to restaurants or eating places unless explicitly requested.\n"
    "2. At each stage, offer AT LEAST 2 distinct choices (e.g., Option A: Visit a landmark, museum, "
    "temple, or park; Option B: Grab a bite or coffee nearby).\n"
    "3. If the user specifies preferences (e.g., 'only South Indian', 'only sightseeing', 'temples'), "
    "strictly tailor recommendations to those preferences.\n"
    "4. Mention venue ratings, locality, and distances (only if location is provided/requested). Refer to the provided LIVE SYSTEM TIME "
    "when building itineraries if no timeframe is specified.\n\n"
    "FEATURE 6 - LOCAL INSIGHTS DIGEST:\n"
    "Combine live places data, ratings, and weather forecasts. Explain explicitly how weather or conditions "
    "influenced your advice.\n\n"
    "GENERAL RULES:\n"
    "- Always include available Ratings (★), Cuisine info, and Locality details in your venue descriptions.\n"
    "- Include distance ONLY when explicitly requested or during itinerary planning.\n"
    "- Use 'search_local_dataset' when asked about specific dish menus, popular dishes, average cost for two, or budget constraints under a certain amount.\n"
    "- Do not invent facts or ratings about places.\n"
    "- Use the provided live system time when evaluating times of day."
)

def generate_response(user_query, user_location=None):
    # Check if the query asks for nearby/distance context
    distance_keywords = ["near", "distance", "close", "km", "minutes", "far"]
    is_distance_requested = any(
        kw in user_query.lower() for kw in distance_keywords
    )

    if is_distance_requested and user_location:
        # Include user's current location context in prompt for calculations
        location_context = f"User's specified location is: {user_location}. Calculate distance from this point."
    else:
        # Strip out system time or auto-location references
        location_context = (
            "Provide general listing with Locality details only. Do NOT add distance or system time calculations. "
            "Ask the user at the end if they want to calculate distance by specifying their location in the sidebar."
        )

    # Combine with retrieved RAG context from vector database
    full_prompt = f"{SYSTEM_PROMPT}\n\nContext Instructions: {location_context}\n\nUser Query: {user_query}"

    # Call your LLM / API here
    # response = llm.generate(full_prompt)
    return response
# ---------------- TTS ----------------

def speak(text):
    try:
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print("[TTS error]", e)
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


# ---------------- Voice Input ----------------

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except Exception:
        return None


# ---------------- Location Detection ----------------

def detect_location():
    # Try ipapi.co first
    try:
        response = requests.get("https://ipapi.co/json/", timeout=8)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city")
            region = data.get("region")
            country = data.get("country_name")
            if city:
                return ", ".join([p for p in [city, region, country] if p])
    except Exception:
        pass

    # Fallback to ip-api.com if ipapi.co fails or times out
    try:
        response = requests.get("http://ip-api.com/json/", timeout=8)
        if response.status_code == 200:
            data = response.json()
            city = data.get("city")
            region = data.get("regionName")
            country = data.get("country")
            if city:
                return ", ".join([p for p in [city, region, country] if p])
    except Exception:
        pass

    return None

# ---------------- Distance Calculation ----------------

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------- Geocoding ----------------

@st.cache_data(show_spinner=False)
def get_coordinates(place_name, geoapify_key=""):
    # Try Geoapify Geocoding if key is provided
    if geoapify_key:
        try:
            url = "https://api.geoapify.com/v1/geocode/search"
            params = {"text": place_name, "apiKey": geoapify_key, "limit": 1}
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            data = res.json()
            if data.get("features"):
                feat = data["features"][0]
                lon, lat = feat["geometry"]["coordinates"]
                address = feat["properties"].get("formatted", place_name)
                return lat, lon, address
        except Exception:
            pass

    # Fallback to OpenStreetMap / Nominatim
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": place_name, "format": "jsonv2", "addressdetails": 1, "limit": 1}
    headers = {"User-Agent": "ollama-local-guide-project"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        results = response.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"]), results[0].get("display_name", place_name)
    except Exception:
        pass

    return None


# ---------------- Input Normalization Helper ----------------

def normalize_input_type(value, default="restaurant"):
    if isinstance(value, dict):
        for k, v in value.items():
            if v is True:
                return k
        return default
    if isinstance(value, list):
        return str(value[0]) if value else default
    if isinstance(value, str) and value.startswith("{"):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                for k, v in parsed.items():
                    if v is True:
                        return k
        except Exception:
            pass
    return str(value).strip().lower() if value else default


# ============================================================
# WEATHER TOOL
# ============================================================

def get_weather_by_name(location_name, geoapify_key=""):
    coords_info = get_coordinates(location_name, geoapify_key)

    if coords_info is None:
        return f"Could not find location or landmark: {location_name}"

    lat, lon, full_address = coords_info

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "hourly": "precipitation_probability,temperature_2m",
            "forecast_days": 1,
            "timezone": "auto"
        }

        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather", {})
        temp = current.get("temperature")
        windspeed = current.get("windspeed")
        hourly = data.get("hourly", {})
        rain_chances = hourly.get("precipitation_probability", [])

        max_rain_chance = max(rain_chances) if isinstance(rain_chances, list) and rain_chances else None

        summary = f"Current weather near {location_name} ({full_address}): {temp}°C, wind {windspeed} km/h."
        if max_rain_chance is not None:
            summary += f" Chance of rain today reaches up to {max_rain_chance}%."

        return summary

    except Exception:
        return f"Weather service temporarily unavailable for {location_name}."


weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get live weather conditions and rain probability for any place.",
        "parameters": {
            "type": "object",
            "properties": {
                "location_name": {"type": "string", "description": "City, landmark, college, or building name"}
            },
            "required": ["location_name"]
        }
    }
}


# ============================================================
# PLACES DATA FETCHING ENGINE (Geoapify + Foursquare + Overpass)
# ============================================================

def fetch_places_geoapify(lat, lon, place_type, cuisine, radius, api_key):
    category_map = {
        "restaurant": "catering.restaurant",
        "cafe": "catering.cafe",
        "tourist_attraction": "tourism.attraction,tourism.sights",
        "hospital": "healthcare.hospital",
        "atm": "service.financial.atm",
        "park": "leisure.park",
        "shopping_mall": "commercial.shopping_mall",
        "place_of_worship": "building.place_of_worship"
    }

    cat = category_map.get(place_type, "catering.restaurant")
    url = "https://api.geoapify.com/v2/places"
    params = {
        "categories": cat,
        "filter": f"circle:{lon},{lat},{radius}",
        "bias": f"proximity:{lon},{lat}",
        "limit": 20,
        "apiKey": api_key
    }

    if cuisine:
        params["conditions"] = cuisine

    res = requests.get(url, params=params, timeout=15)
    res.raise_for_status()
    data = res.json()

    results = []
    for feat in data.get("features", []):
        props = feat.get("properties", {})
        name = props.get("name")
        if not name:
            continue

        p_lat = props.get("lat")
        p_lon = props.get("lon")
        dist = haversine_distance(lat, lon, p_lat, p_lon) if p_lat and p_lon else None

        # Filter by cuisine keyword if requested
        found_cuisine = props.get("datasource", {}).get("raw", {}).get("cuisine", "")
        if cuisine and cuisine.lower() not in name.lower() and cuisine.lower() not in str(found_cuisine).lower():
            continue

        results.append({
            "name": name,
            "address": props.get("formatted"),
            "cuisine": found_cuisine or cuisine,
            "distance_m": round(dist) if dist else None,
            "rating": None,
            "source": "Geoapify"
        })

    return results


def fetch_places_foursquare(lat, lon, place_type, cuisine, radius, api_key):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": api_key
    }
    params = {
        "ll": f"{lat},{lon}",
        "radius": radius,
        "limit": 20,
        "fields": "fsq_id,name,location,categories,distance,rating,price"
    }

    query_term = cuisine if cuisine else place_type.replace("_", " ")
    params["query"] = query_term

    res = requests.get(url, headers=headers, params=params, timeout=15)
    res.raise_for_status()
    data = res.json()

    results = []
    for item in data.get("results", []):
        name = item.get("name")
        if not name:
            continue

        rating = item.get("rating")
        rating_str = f"{round(rating / 2, 1)} ★" if rating else None
        price = item.get("price")
        price_str = "$" * price if price else None

        cats = [c.get("name") for c in item.get("categories", [])]

        results.append({
            "name": name,
            "address": item.get("location", {}).get("formatted_address"),
            "cuisine": ", ".join(cats) if cats else cuisine,
            "distance_m": item.get("distance"),
            "rating": rating_str,
            "price": price_str,
            "source": "Foursquare"
        })

    return results


def fetch_places_overpass(lat, lon, place_type, radius):
    tag_map = {
        "restaurant": '"amenity"="restaurant"',
        "cafe": '"amenity"="cafe"',
        "tourist_attraction": '"tourism"="attraction"',
        "hospital": '"amenity"="hospital"',
        "atm": '"amenity"="atm"',
        "park": '"leisure"="park"',
        "shopping_mall": '"shop"="mall"',
        "place_of_worship": '"amenity"="place_of_worship"'
    }

    tag_filter = tag_map.get(place_type, '"amenity"="restaurant"')
    url = "https://overpass-api.de/api/interpreter"
    query = f"[out:json][timeout:15];node[{tag_filter}](around:{radius},{lat},{lon});out center 15;"

    res = requests.post(url, data=query.encode("utf-8"), headers={"User-Agent": "ollama-local-guide"}, timeout=20)
    res.raise_for_status()
    data = res.json()

    results = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        p_lat, p_lon = el.get("lat"), el.get("lon")
        dist = haversine_distance(lat, lon, p_lat, p_lon) if p_lat and p_lon else None

        results.append({
            "name": name,
            "address": tags.get("addr:street"),
            "cuisine": tags.get("cuisine"),
            "distance_m": round(dist) if dist else None,
            "rating": None,
            "source": "OpenStreetMap"
        })

    return results


def find_nearby_places_combined(location_name, place_type="restaurant", cuisine=None, geoapify_key="", foursquare_key=""):
    clean_place_type = normalize_input_type(place_type, "restaurant")
    clean_cuisine = normalize_input_type(cuisine, "") if cuisine else None

    coords_info = get_coordinates(location_name, geoapify_key)
    if coords_info is None:
        return f"Could not locate '{location_name}'. Try including city or district name."

    lat, lon, full_address = coords_info
    combined_places = []
    seen_names = set()

    # 1. Fetch from Geoapify if Key exists
    if geoapify_key:
        try:
            g_places = fetch_places_geoapify(lat, lon, clean_place_type, clean_cuisine, 2500, geoapify_key)
            for p in g_places:
                if p["name"].lower() not in seen_names:
                    seen_names.add(p["name"].lower())
                    combined_places.append(p)
        except Exception:
            pass

    # 2. Fetch/Enrich with Foursquare if Key exists
    if foursquare_key:
        try:
            f_places = fetch_places_foursquare(lat, lon, clean_place_type, clean_cuisine, 2500, foursquare_key)
            for p in f_places:
                name_key = p["name"].lower()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    combined_places.append(p)
                else:
                    # Enrich existing place with Foursquare Rating
                    for existing in combined_places:
                        if existing["name"].lower() == name_key and p.get("rating"):
                            existing["rating"] = p["rating"]
        except Exception:
            pass

    # 3. Fallback to Overpass API if no results were retrieved
    if not combined_places:
        try:
            o_places = fetch_places_overpass(lat, lon, clean_place_type, 2500)
            for p in o_places:
                if p["name"].lower() not in seen_names:
                    seen_names.add(p["name"].lower())
                    combined_places.append(p)
        except Exception:
            pass

    if not combined_places:
        return f"No {clean_place_type}s found near '{location_name}' ({full_address})."

    # Sort strictly by distance
    combined_places.sort(key=lambda p: p["distance_m"] if p["distance_m"] is not None else float("inf"))

    header = f"{clean_place_type.capitalize()}s near '{location_name}' ({full_address}):\n"
    lines = []
    for p in combined_places[:12]:  # Top 12 closest results
        line = f"- {p['name']}"
        if p.get("rating"):
            line += f" | Rating: {p['rating']}"
        if p.get("distance_m") is not None:
            line += f" | {p['distance_m']}m away"
        if p.get("cuisine"):
            line += f" | Cuisine/Category: {p['cuisine']}"
        if p.get("address"):
            line += f" | Address: {p['address']}"
        lines.append(line)

    return header + "\n".join(lines)


places_tool = {
    "type": "function",
    "function": {
        "name": "find_nearby_places",
        "description": (
            "Find places with exact ratings, chains, and distance. "
            "Supports categories: restaurant, cafe, tourist_attraction, hospital, atm, park, "
            "shopping_mall, place_of_worship. Pass 'cuisine' for specific food requests (e.g., south_indian)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location_name": {
                    "type": "string",
                    "description": "City, landmark, college, or building name"
                },
                "place_type": {
                    "type": "string",
                    "enum": [
                        "restaurant",
                        "cafe",
                        "tourist_attraction",
                        "hospital",
                        "atm",
                        "park",
                        "shopping_mall",
                        "place_of_worship"
                    ]
                },
                "cuisine": {
                    "type": "string",
                    "description": "Optional cuisine type (e.g., south_indian, fast_food, chinese, italian, north_indian)"
                }
            },
            "required": ["location_name", "place_type"]
        }
    }
}


# ============================================================
# DATASET SEARCH TOOL (RAG)
# ============================================================

def search_local_dataset(query_text, n_results=5):
    try:
        results = dataset_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        formatted_results = []
        if results and "documents" in results and results["documents"]:
            for doc in results["documents"][0]:
                formatted_results.append(f"- {doc}")
                
        return "\n".join(formatted_results) if formatted_results else "No matching local dataset records found."
    except Exception as e:
        return f"Dataset search unavailable: {str(e)}"


dataset_tool = {
    "type": "function",
    "function": {
        "name": "search_local_dataset",
        "description": "Search local database for dish menus, popular dishes, average cost for two, or venue specifics.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_text": {
                    "type": "string",
                    "description": "Keywords, dish names, or venue details to search (e.g. 'South Indian Butter Dosa', 'cost under 400')"
                }
            },
            "required": ["query_text"]
        }
    }
}

# ============================================================
# MULTI-ROUND OLLAMA LOOP
# ============================================================
def chat_with_tools(messages, model="llama3.2", geoapify_key="", foursquare_key="", max_rounds=7):
    # Add dataset_tool to the active tools list
    tools = [places_tool, weather_tool, dataset_tool]

    now = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    system_time_prompt = f"\n\nLIVE SYSTEM TIME: {now}. Reference this time for schedule/weather context."

    working_messages = list(messages)
    if working_messages and working_messages[0]["role"] == "system":
        working_messages[0] = {
            "role": "system",
            "content": SYSTEM_PROMPT + system_time_prompt
        }

    for _ in range(max_rounds):

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
                "messages": working_messages,
                "tools": tools,
                "stream": False
            },
            timeout=120
        )

        response.raise_for_status()
        message = response.json()["message"]

        if not message.get("tool_calls"):
            return message.get("content", "I could not generate a response.")

        working_messages.append(message)

        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            args = tool_call["function"]["arguments"]

            if func_name == "find_nearby_places":
                result = find_nearby_places_combined(
                    location_name=args.get("location_name"),
                    place_type=args.get("place_type", "restaurant"),
                    cuisine=args.get("cuisine"),
                    geoapify_key=geoapify_key,
                    foursquare_key=foursquare_key
                )

            elif func_name == "get_weather":
                result = get_weather_by_name(
                    location_name=args.get("location_name"),
                    geoapify_key=geoapify_key
                )

            # Add execution handler for the dataset tool
            elif func_name == "search_local_dataset":
                result = search_local_dataset(
                    query_text=args.get("query_text", "")
                )

            else:
                result = "Unknown tool"

            working_messages.append({
                "role": "tool",
                "content": result
            })

    return "I gathered information but could not complete the response in time."


# ---------------- Streaming Effect ----------------

def stream_text(text, delay=0.02):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


# ============================================================
# STREAMLIT UI
# ============================================================
# ============================================================
# INITIALIZE DATASET ON STARTUP
# ============================================================

@st.cache_resource(show_spinner="Loading Zomato Dataset into Vector Store...")
def initialize_dataset():
    # Reads the CSV and builds the local ChromaDB vector store once
    success = load_dataset_into_vectorstore("zomato_restaurants_in_india.csv")
    return success

# Trigger the dataset load when Streamlit starts
dataset_loaded = initialize_dataset()
st.set_page_config(page_title="Smart Local Guide", page_icon="🧭")
st.title("🧭 Smart Local Guide")
st.caption("Multi-API Local Assistant (Geoapify + Foursquare + Overpass + Ollama)")

with st.sidebar:
    st.subheader("API Keys (For Chains & Ratings)")
    geoapify_key = st.text_input("Geoapify Key", value=DEFAULT_GEOAPIFY_KEY, type="password")
    foursquare_key = st.text_input("Foursquare Key", value=DEFAULT_FOURSQUARE_KEY, type="password")

    st.subheader("Settings")
    voice_output = st.toggle("Speak replies out loud", value=False)

    st.subheader("Model")
    AVAILABLE_MODELS = ["llama3.2", "llama3.1", "qwen2.5", "mistral"]
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = "llama3.2"

    selected_model = st.selectbox(
        "Choose Model",
        options=AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.selected_model)
    )
    st.session_state.selected_model = selected_model

    st.subheader("Location")

    if "user_location" not in st.session_state:
        st.session_state.user_location = ""

    # Button to auto-detect
    if st.button("Detect my location"):
        loc = detect_location()
        if loc:
            st.session_state.user_location = loc
            st.success("Detected: " + loc)
        else:
            st.error("Could not detect automatically. Please type your location below.")

    # Manual input fallback (preserves chat history across reruns)
    manual_loc = st.text_input(
        "Or enter your location manually:",
        value=st.session_state.user_location,
        placeholder="e.g. Connaught Place, New Delhi"
    )

    if manual_loc:
        st.session_state.user_location = manual_loc

    if st.session_state.user_location:
        st.caption("Active Location: " + st.session_state.user_location)
    st.subheader("Voice Input")
    audio_value = st.audio_input("Record voice prompt")

    if st.button("Clear conversation"):
        st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        st.rerun()


# ---------------- Conversation State ----------------

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# Display Conversation
for msg in st.session_state.messages:
    if msg["role"] in ("user", "assistant"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# ---------------- User Input Handling ----------------

typed_input = st.chat_input("Ask about South Indian food, food chains, or plans near any landmark...")
user_input = None

if typed_input:
    user_input = typed_input
elif audio_value is not None and st.session_state.get("last_audio_id") != id(audio_value):
    st.session_state.last_audio_id = id(audio_value)
    transcribed = transcribe_audio(audio_value.getvalue())
    if transcribed:
        user_input = transcribed
    else:
        st.warning("Could not transcribe voice message.")


# ---------------- Process Request ----------------

if user_input:

    if st.session_state.user_location and "near me" in user_input.lower():
        user_input = re.sub("near me", "near " + st.session_state.user_location, user_input, flags=re.IGNORECASE)

    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner(f"Fetching live data & reasoning ({st.session_state.selected_model})..."):
            reply = chat_with_tools(
                st.session_state.messages,
                model=st.session_state.selected_model,
                geoapify_key=geoapify_key,
                foursquare_key=foursquare_key
            )

        st.write_stream(stream_text(reply))

    st.session_state.messages.append({"role": "assistant", "content": reply})

    if voice_output:
        speak(reply)