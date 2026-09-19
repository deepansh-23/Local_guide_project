# 🧭 Smart Local Guide

An AI-powered local travel and area discovery assistant built with **Python, Streamlit, and Google Gemini**.

## ✨ Features

* 🗺️ **Itinerary Planner** — Create personalized itineraries based on location, duration, budget, interests, food preferences, and group type.
* 📍 **Places Near You** — Find food, hotels, tourist spots, shopping, hospitals, ATMs, parks, landmarks, and hidden gems.
* 🏙️ **Area Summarizer** — Get an AI-generated overview of a neighborhood.
* ☕ **Quiet Work Cafes** — Find cafes suitable for studying and working.
* 🏥 **Medical Care** — Find hospitals, urgent care, and late-night pharmacies.
* 💾 **Separate History** — Each feature maintains its own saved results.
* 🔊 **Text-to-Speech** — Listen to generated itineraries.
* 📄 **PDF Export** — Save generated results as PDFs.

## 🛠️ Technologies

* Python
* Streamlit
* Google Gemini API
* OpenAI Python SDK
* DuckDuckGo Search
* gTTS
* FPDF
* Git & GitHub
* Render

## 📁 Project Structure

```text
Smart-Local-Guide/
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Run Locally

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Smart-Local-Guide
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Set your Gemini API key as:

```text
GEMINI_API_KEY=YOUR_API_KEY
```

Run the application:

```bash
streamlit run app.py
```

## 🌐 Deployment

The application is deployed using **Render** and connected to GitHub.

After making changes:

```bash
git add .
git commit -m "Updated Smart Local Guide"
git push origin main
```

Render can automatically redeploy the latest version.

## 🔐 Security

Never upload your Gemini API key to GitHub. Use environment variables instead.

## 🚀 Future Improvements

* Interactive maps and GPS
* Accurate distance calculation
* Persistent user accounts and history
* Weather integration
* Hotel and restaurant booking
* Multi-language support

## 👨‍💻 Author

**Deepansh Maurya**
M.Sc. Informatics, University of Delhi

---

*Built as an AI-powered local discovery and travel assistant.*
