"""
FastAPI backend for Dev Card Generator.
Exposes REST endpoints and runs the card generation pipeline via Groq.
Features:
  - GitHub / GitLab / LinkedIn OAuth authentication
  - Card generation with theme/layout overrides
  - Analytics (view counting)
"""

import os
import json
import asyncio
import pathlib
import secrets
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load .env relative to this file so it works regardless of cwd
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import httpx

from agent import run_pipeline

# ── Config ─────────────────────────────────────────────────────────────────────
SESSION_SECRET    = os.getenv("SESSION_SECRET_KEY", "dev-secret-change-me")
BACKEND_URL       = os.getenv("BACKEND_URL", "http://localhost:8080")
FRONTEND_URL      = os.getenv("FRONTEND_URL") or (BACKEND_URL if BACKEND_URL != "http://localhost:8080" else "http://localhost:3000")

# GitHub OAuth
GITHUB_CLIENT_ID     = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# GitLab OAuth
GITLAB_CLIENT_ID     = os.getenv("GITLAB_CLIENT_ID", "")
GITLAB_CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET", "")

# LinkedIn OAuth
LINKEDIN_CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")

signer = URLSafeTimedSerializer(SESSION_SECRET)

ANALYTICS_FILE = pathlib.Path(__file__).parent.parent / "frontend" / "analytics.json"

# ── Session helpers ────────────────────────────────────────────────────────────
def create_session_token(data: dict) -> str:
    return signer.dumps(data)

def read_session_token(token: str) -> dict | None:
    try:
        return signer.loads(token, max_age=86400 * 7)  # 7 days
    except (BadSignature, SignatureExpired):
        return None

# ── Analytics helpers ──────────────────────────────────────────────────────────
def load_analytics() -> dict:
    if ANALYTICS_FILE.exists():
        try:
            return json.loads(ANALYTICS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_analytics(data: dict):
    ANALYTICS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

# ── Services ───────────────────────────────────────────────────────────────────
# (no ADK session service needed — pipeline runs directly)

# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    cards_dir = pathlib.Path(__file__).parent.parent / "frontend" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not ANALYTICS_FILE.exists():
        save_analytics({})
    yield

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="GitHub Dev Card Generator",
    description="AI-powered developer profile cards using Groq + Llama",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ─────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    username: str
    platform: str = "github"          # "github" | "gitlab"
    theme_override: str = "auto"      # "auto" | theme name
    layout: str = "standard"          # "standard" | "compact" | "wide"

class GenerateResponse(BaseModel):
    username: str
    card_url: str
    message: str

# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}

# ── GitHub OAuth ───────────────────────────────────────────────────────────────
@app.get("/auth/github")
async def auth_github():
    """Redirect user to GitHub OAuth authorization page."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured. Add GITHUB_CLIENT_ID to .env")
    state = secrets.token_hex(16)
    callback = f"{BACKEND_URL}/auth/callback"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={callback}"
        f"&scope=read:user"
        f"&state={state}"
    )
    return RedirectResponse(url=url)

@app.get("/auth/callback")
async def auth_callback(code: str, state: str, response: Response):
    """Exchange OAuth code for access token and set session cookie."""
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured.")
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from GitHub.")

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github.v3+json"},
        )
        user = user_resp.json()

    session_data = {
        "login": user.get("login"),
        "name": user.get("name") or user.get("login"),
        "avatar_url": user.get("avatar_url"),
        "access_token": access_token,
    }
    token = create_session_token(session_data)
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/", status_code=302)
    redirect.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return redirect

@app.get("/auth/gitlab")
async def auth_gitlab():
    """Redirect user to GitLab OAuth authorization page."""
    if not GITLAB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitLab OAuth not configured. Add GITLAB_CLIENT_ID to .env")
    state = secrets.token_hex(16)
    callback = f"{BACKEND_URL}/auth/callback/gitlab"
    url = (
        f"https://gitlab.com/oauth/authorize"
        f"?client_id={GITLAB_CLIENT_ID}"
        f"&redirect_uri={callback}"
        f"&response_type=code"
        f"&scope=read_user"
        f"&state={state}"
    )
    return RedirectResponse(url=url)

@app.get("/auth/callback/gitlab")
async def auth_callback_gitlab(code: str, state: str, response: Response):
    """Exchange GitLab OAuth code for token."""
    if not GITLAB_CLIENT_ID or not GITLAB_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="GitLab OAuth not configured.")
    callback = f"{BACKEND_URL}/auth/callback/gitlab"
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://gitlab.com/oauth/token",
            json={
                "client_id": GITLAB_CLIENT_ID,
                "client_secret": GITLAB_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from GitLab.")
        user_resp = await client.get(
            "https://gitlab.com/api/v4/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_resp.json()
    session_data = {
        "login": user.get("username"),
        "name": user.get("name") or user.get("username"),
        "avatar_url": user.get("avatar_url"),
        "access_token": access_token,
        "provider": "gitlab",
    }
    token = create_session_token(session_data)
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/", status_code=302)
    redirect.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return redirect

@app.get("/auth/linkedin")
async def auth_linkedin():
    """Redirect user to LinkedIn OAuth authorization page."""
    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(status_code=501, detail="LinkedIn OAuth not configured. Add LINKEDIN_CLIENT_ID to .env")
    state = secrets.token_hex(16)
    callback = f"{BACKEND_URL}/auth/callback/linkedin"
    url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={LINKEDIN_CLIENT_ID}"
        f"&redirect_uri={callback}"
        f"&scope=openid%20profile"
        f"&state={state}"
    )
    return RedirectResponse(url=url)

@app.get("/auth/callback/linkedin")
async def auth_callback_linkedin(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    response: Response = None,
):
    """Exchange LinkedIn OAuth code for token."""
    # Handle error responses from LinkedIn (e.g. invalid_scope)
    if error:
        detail = error_description or error
        return RedirectResponse(
            url=f"{FRONTEND_URL}/?auth_error={detail}",
            status_code=302,
        )
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")
    if not LINKEDIN_CLIENT_ID or not LINKEDIN_CLIENT_SECRET:
        raise HTTPException(status_code=501, detail="LinkedIn OAuth not configured.")
    callback = f"{BACKEND_URL}/auth/callback/linkedin"
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token from LinkedIn.")
        user_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_resp.json()
    session_data = {
        "login": user.get("sub"),
        "name": user.get("name"),
        "avatar_url": user.get("picture", ""),
        "access_token": access_token,
        "provider": "linkedin",
    }
    token = create_session_token(session_data)
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/", status_code=302)
    redirect.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return redirect


@app.get("/auth/me")
async def auth_me(request: Request):
    """Return current authenticated user info."""
    token = request.cookies.get("session")
    if not token:
        return JSONResponse({"authenticated": False})
    data = read_session_token(token)
    if not data:
        return JSONResponse({"authenticated": False})
    return JSONResponse({
        "authenticated": True,
        "login": data.get("login"),
        "name": data.get("name"),
        "avatar_url": data.get("avatar_url"),
        "provider": data.get("provider", "github"),
    })

@app.get("/auth/logout")
async def auth_logout(response: Response):
    """Clear the session cookie."""
    resp = RedirectResponse(url=f"{FRONTEND_URL}/", status_code=302)
    resp.delete_cookie("session")
    return resp

# ── Analytics ──────────────────────────────────────────────────────────────────
@app.post("/analytics/view/{username}")
async def record_view(username: str):
    """Increment view count for a card."""
    analytics = load_analytics()
    username = username.lower()
    analytics[username] = analytics.get(username, 0) + 1
    save_analytics(analytics)
    return {"username": username, "views": analytics[username]}

@app.get("/analytics/{username}")
async def get_views(username: str):
    """Get view count for a card."""
    analytics = load_analytics()
    count = analytics.get(username.lower(), 0)
    return {"username": username, "views": count}

@app.get("/analytics")
async def get_top_cards():
    """Return top 10 most-viewed cards."""
    analytics = load_analytics()
    top = sorted(analytics.items(), key=lambda x: x[1], reverse=True)[:10]
    return {"top_cards": [{"username": u, "views": v} for u, v in top]}

# ── Generate ───────────────────────────────────────────────────────────────────
@app.post("/generate", response_model=GenerateResponse)
async def generate_card(request: GenerateRequest):
    """
    Generate a dev card for a GitHub, GitLab, or LinkedIn username.
    Runs the Groq-powered pipeline.
    """
    username = request.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await asyncio.to_thread(
                run_pipeline,
                username=username,
                platform=request.platform,
                theme_override=request.theme_override,
                layout=request.layout,
            )
            return GenerateResponse(**result)

        except ValueError as e:
            # Profile not found or scrape error — don't retry
            raise HTTPException(status_code=404, detail=str(e))

        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate_limit" in err_str.lower()

            if is_rate_limit and attempt < max_retries - 1:
                await asyncio.sleep(2 ** (attempt + 1))
                continue

            if is_rate_limit:
                raise HTTPException(status_code=429, detail="Groq API rate limit hit. Please wait a moment and try again.")

            raise HTTPException(status_code=500, detail=f"Error generating card for '{username}': {err_str}")

# ── Card Serve ─────────────────────────────────────────────────────────────────
@app.get("/card/{username}", response_class=HTMLResponse)
async def get_card(username: str):
    """Serve a saved dev card HTML file."""
    card_path = pathlib.Path(__file__).parent.parent / "frontend" / "cards" / f"{username}.html"
    if not card_path.exists():
        raise HTTPException(status_code=404, detail=f"Card not found for '{username}'")
    return HTMLResponse(content=card_path.read_text(encoding="utf-8"))

# ── Serve Frontend ─────────────────────────────────────────────────────────────
frontend_dir = pathlib.Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
