# GitHub & LinkedIn Dev Card Generator 🚀

Generate beautiful, AI-powered developer profile cards from any public GitHub, GitLab, or LinkedIn username using **Groq (Llama 3.3)**, **FastAPI**, and real-time **LinkedIn scraping**.

![Groq](https://img.shields.io/badge/Groq-Llama_3.3-orange?logo=groq&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Available_Now-success?style=flat)](https://github-dev-card-generator-15593284604.europe-west1.run.app/)

## 🌐 Live Demo

You can try out the live version of the generator deployed on Google Cloud Run here:
👉 **[Live Application Link](https://github-dev-card-generator-15593284604.europe-west1.run.app/)**

---

## ✨ Features

- **AI-Powered Insights:** Uses **Groq (Llama 3.3)** to analyze developer profiles, summarize experience, identify top skills, and generate custom developer vibes and fun facts.
- **Real-Time LinkedIn Scraping:** Fully integrated with **Apify's HarvestAPI LinkedIn Scraper** (and Proxycurl) to fetch live, real profile data including headlines, work experience, location, follower counts, and skills.
- **Base64 Avatar Auto-Embedding (No Broken Images):** Bypasses strict LinkedIn CDN hotlink protection and prevents link expiration by downloading profile pictures server-side and automatically embedding them as self-contained **Base64 Data URLs**. Your cards load instantly, offline-resilient, and will never break!
- **High-Performance Smart Caching:** Caches scraped profile data locally. Clicking through different themes and layouts loads data **instantly in under 2 seconds**, preserving scraper API credits and eliminating redundant scraping delay.
- **Premium Design Aesthetics:** Sleek, modern developer card UI featuring rich gradients, interactive light/dark/neon themes, active hover states, and smooth CSS glassmorphism effects.
- **Advanced Customization:** 
  - **Themes:** Hacker, Builder, Researcher, Designer, Open Source Hero, Light, and Neon.
  - **Layouts:** Standard, Compact, and Wide options.
- **One-Click Sharing & Exports:** 
  - Copy the direct card URL to share your profile.
  - Download fully-rendered, high-resolution cards as **PNG** or **PDF** with one click.
- **Integrated View Analytics:** Automatically tracks and displays live view counts on the generated cards.
- **Secure Architecture:** Pre-configured `.gitignore` safeguards your private `.env` configurations and API tokens.

---

## 📂 Project Structure

```text
github-dev-card-generator/
│
├── frontend/                  # Web Interface
│   ├── index.html             # Main HTML structure
│   ├── style.css              # External stylesheet
│   ├── script.js              # API calls, state management & exports
│   └── cards/                 # Generated HTML Dev Cards
│       └── cache/             # Local scraped profile JSON cache
│
├── backend/                   # FastAPI Server
│   ├── main.py                # REST API endpoints & server setup
│   ├── agent.py               # AI Pipeline & caching orchestrator
│   ├── mcp_server.py          # FastMCP server, scrapers & base64 helper
│   └── requirements.txt       # Python dependencies
│
├── Dockerfile                 # Unified container deployment
├── docker-compose.yml         # Docker orchestration
├── .gitignore                 # Ignored files (.env, .venv, cards, cache, etc.)
└── README.md                  # This documentation
```

---

## 🚀 How to Run Locally

### Prerequisites
- Docker & Docker Compose (optional, for containerized run)
- A **Groq API Key** (obtain from the [Groq Console](https://console.groq.com/))
- An **Apify API Token** (optional, for real-time LinkedIn scraping via `harvestapi/linkedin-profile-scraper`)

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ayus1234/github-dev-card-generator.git
   cd github-dev-card-generator
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the `backend/` directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   APIFY_API_TOKEN=your_apify_api_token_here
   ```

3. **Start the application with Docker:**
   ```bash
   docker-compose up --build
   ```

   *Alternatively, run without Docker:*
   *   **Backend:** `cd backend && pip install -r requirements.txt && python main.py`
   *   **Frontend:** Serve the `frontend` folder using `python -m http.server 3000`

4. **Access the App:**
   - Open your browser and go to `http://localhost:3000` (or the backend at `http://localhost:8080`)
   - **Backend API Docs:** Available at `http://localhost:8080/docs`

---

## 🤝 Built With

- **[Groq AI](https://groq.com)** — Fast inference with Llama 3.3
- **[FastAPI](https://fastapi.tiangolo.com/)** — High-performance Python backend framework
- **[Apify](https://apify.com/)** — Reliable, cookies-free LinkedIn scraping via HarvestAPI
- **Vanilla HTML / CSS / JS** — Ultra-lightweight, blazing-fast, and premium glassmorphism styling
- **Docker Compose** — Effortless multi-container orchestration

*Built with ❤️ using Groq + Llama 3.3*
