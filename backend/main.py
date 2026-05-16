"""
FastAPI backend for GitHub Dev Card Generator.
Exposes REST endpoints and runs the ADK agent via Runner.
"""

import os
import json
import asyncio
import pathlib
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load .env relative to this file so it works regardless of cwd
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agent import github_card_agent

# ── Services ──────────────────────────────────────────────────────────────────
session_service = InMemorySessionService()

runner = Runner(
    agent=github_card_agent,
    app_name="github_card_generator",
    session_service=session_service,
)

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create static/cards directory at startup
    cards_dir = pathlib.Path(__file__).parent.parent / "frontend" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    yield

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="GitHub Dev Card Generator",
    description="AI-powered developer profile cards using Google ADK + Gemini",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware — allow all origins for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (CSS, JS) from frontend folder
app.mount("/frontend", StaticFiles(directory=str(pathlib.Path(__file__).parent.parent / "frontend")), name="frontend")

# ── Models ────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    username: str

class GenerateResponse(BaseModel):
    username: str
    card_url: str
    message: str

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main frontend application."""
    index_path = pathlib.Path(__file__).parent.parent / "frontend" / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "ok"}


@app.post("/generate", response_model=GenerateResponse)
async def generate_card(request: GenerateRequest):
    """
    Generate a dev card for a GitHub username.
    Runs the ADK agent through the full 4-step pipeline.
    """
    username = request.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    try:
        # Create or reuse session by username
        session_id = f"session_{username}"
        user_id = f"user_{username}"

        session = await session_service.get_session(
            app_name="github_card_generator",
            user_id=user_id,
            session_id=session_id,
        )

        if session is None:
            session = await session_service.create_session(
                app_name="github_card_generator",
                user_id=user_id,
                session_id=session_id,
            )

        # Run the agent
        message = types.Content(
            role="user",
            parts=[types.Part(text=f"Generate a dev card for GitHub user: {username}")],
        )

        final_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        final_text = part.text  # Keep last text response

        # Check if card was saved
        card_path = pathlib.Path(__file__).parent.parent / "frontend" / "cards" / f"{username}.html"
        if card_path.exists():
            card_url = f"/card/{username}"
        else:
            card_url = ""

        return GenerateResponse(
            username=username,
            card_url=card_url,
            message=final_text or f"Dev card generated for {username}!",
        )

    except Exception as e:
        err_str = str(e)
        status = 500
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            status = 429
            detail = f"Gemini API rate limit hit. Please wait a moment and try again."
        else:
            detail = f"Error generating card for '{username}': {err_str}"
        raise HTTPException(status_code=status, detail=detail)


@app.get("/card/{username}", response_class=HTMLResponse)
async def get_card(username: str):
    """Serve a saved dev card HTML file."""
    card_path = pathlib.Path(__file__).parent.parent / "frontend" / "cards" / f"{username}.html"
    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"Card not found for '{username}'")
    return HTMLResponse(content=card_path.read_text(encoding="utf-8"))


# ── Run with uvicorn ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
