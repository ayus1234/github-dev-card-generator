# GitHub Dev Card Generator 🚀

Generate beautiful, AI-powered developer profile cards from any public GitHub username using **Gemini AI**, **Google ADK**, and **FastAPI**.

![GitHub Dev Card Generator](https://img.shields.io/badge/Gemini-AI-blue?logo=google&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Available_Now-success?style=flat)](https://github-dev-card-generator-15593284604.europe-west1.run.app/)

## 🌐 Live Demo

You can try out the live version of the generator deployed on Google Cloud Run here:
👉 **[Live Application Link](https://github-dev-card-generator-15593284604.europe-west1.run.app/)**

---

## ✨ Features

- **AI-Powered Insights:** Uses Gemini AI (via Google ADK and FastMCP) to analyze GitHub profiles and generate custom developer summaries.
- **Premium Design Aesthetics:** Features dynamic backgrounds, smooth micro-animations, and modern UI tokens (glassmorphism effects).
- **Official Branding:** Uses the official GitHub SVG logo for a professional look.
- **Modular Codebase:** Cleanly separated HTML, external CSS (`style.css`), and external JavaScript (`script.js`).
- **One-Click Sharing:** Instantly copy the generated card URL to share your profile.
- **Dockerized Setup:** Easily run the entire application (both frontend and backend) using Docker Compose.
- **Security First:** Pre-configured `.gitignore` prevents sensitive `.env` files and API keys from leaking to version control.

---

## 📂 Project Structure

```text
github-dev-card-generator/
│
├── frontend/                  # Web Interface
│   ├── index.html             # Main HTML structure
│   ├── style.css              # External stylesheet
│   ├── script.js              # API calls and UI state
│   └── cards/                 # Generated HTML Dev Cards
│
├── backend/                   # FastAPI Server
│   ├── main.py                # REST API endpoints & server setup
│   ├── agent.py               # Google ADK agent configuration for Gemini
│   ├── mcp_server.py          # FastMCP server logic
│   └── requirements.txt       # Python dependencies
│
├── Dockerfile                 # Unified container deployment
├── docker-compose.yml         # Docker orchestration
├── .gitignore                 # Ignored files (.env, .venv, etc.)
└── README.md                  # This documentation
```

---

## 🚀 How to Run Locally

### Prerequisites
- Docker & Docker Compose
- A Gemini API Key from Google AI Studio

### Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ayus1234/github-dev-card-generator.git
   cd github-dev-card-generator
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the `backend/` directory:
   ```bash
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Start the application with Docker:**
   ```bash
   docker-compose up --build
   ```

4. **Access the App:**
   - Open your browser and go to `http://localhost:8080`
   - **Backend API Docs:** Available at `http://localhost:8080/docs`

---

## 🔮 Future Scope and Improvements

- **Authentication Integration:** Allow users to log in with their GitHub account to generate private profile cards.
- **Card Customization:** Add themes (light, dark, colorful) and layout options for the generated cards.
- **Export Formats:** Provide functionality to download the generated dev card as a high-resolution PNG or PDF.
- **More Platforms:** Extend support to generate cards from other developer platforms like GitLab or Bitbucket.
- **Analytics:** Add simple analytics to track how many times a shared card has been viewed.

---

## 🤝 Built With

- [Google ADK](https://github.com/google/adk-python)
- [FastAPI](https://fastapi.tiangolo.com/)
- Vanilla HTML / CSS / JS
- Docker Compose

*Built with ❤️ using Gemini AI*
