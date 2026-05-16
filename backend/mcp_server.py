"""
MCP Server for GitHub Dev Card Generator.
Exposes 4 tools via FastMCP:
  1. scrape_github   — fetch public GitHub profile data
  2. analyze_profile — AI-powered profile analysis via Gemini
  3. generate_card_html — render a themed HTML dev card
  4. save_card       — persist the card to disk
"""

import os
import json
import pathlib
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai

# Load .env relative to this file so it works regardless of cwd
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# ── Gemini client setup ──────────────────────────────────────────────────────
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-2.0-flash-lite"

# ── FastMCP server ────────────────────────────────────────────────────────────
mcp = FastMCP("GitHubCardTools")

# ─────────────────────────────────────────────────────────────────────────────
# Tool 1: Scrape GitHub
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def scrape_github(username: str) -> str:
    """
    Fetch public GitHub profile data for a given username.
    Returns JSON with: name, bio, location, public_repos, followers,
    avatar_url, top 6 repos (name, stars, language, description),
    and aggregated language stats.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    with httpx.Client(timeout=30) as client:
        # Fetch user profile
        user_resp = client.get(
            f"https://api.github.com/users/{username}", headers=headers
        )
        if user_resp.status_code == 404:
            return json.dumps({"error": f"User '{username}' not found."})
        user_resp.raise_for_status()
        user = user_resp.json()

        # Fetch repos sorted by stars
        repos_resp = client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "stars", "direction": "desc", "per_page": 30},
            headers=headers,
        )
        repos_resp.raise_for_status()
        repos = repos_resp.json()

    # Top 6 repos
    top_repos = [
        {
            "name": r["name"],
            "stars": r["stargazers_count"],
            "language": r["language"],
            "description": r["description"] or "",
        }
        for r in repos[:6]
    ]

    # Aggregate languages
    lang_count: dict[str, int] = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1
    top_languages = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:8]

    result = {
        "username": username,
        "name": user.get("name") or username,
        "bio": user.get("bio") or "",
        "location": user.get("location") or "Earth",
        "avatar_url": user.get("avatar_url", ""),
        "public_repos": user.get("public_repos", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "top_repos": top_repos,
        "top_languages": [{"language": lang, "count": cnt} for lang, cnt in top_languages],
    }
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2: Analyze Profile
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def analyze_profile(github_data: str) -> str:
    """
    Analyze a developer's GitHub profile using Gemini AI.
    Input: JSON string of github profile data from scrape_github.
    Returns JSON with: developer_vibe, top_skills, fun_fact, card_theme.
    card_theme is one of: hacker, builder, researcher, designer, open-source-hero.
    """
    prompt = f"""You are analyzing a GitHub developer profile. Based on the following data, provide a JSON response with exactly these fields:

1. "developer_vibe": A single catchy sentence describing this developer's personality/style (e.g., "A relentless systems architect who speaks fluent kernel")
2. "top_skills": A list of exactly 3 key technical skills inferred from their repos and languages
3. "fun_fact": A clever, specific observation inferred from their repos (be creative but factual)
4. "card_theme": Choose exactly ONE from: "hacker", "builder", "researcher", "designer", "open-source-hero"
   - hacker: systems programming, security, low-level work
   - builder: web apps, tools, frameworks, lots of repos
   - researcher: ML, data science, academic projects
   - designer: frontend, UI/UX, CSS-heavy repos
   - open-source-hero: many stars, widely-used projects, community contributor

GitHub Profile Data:
{github_data}

Respond with ONLY valid JSON, no markdown, no code fences."""

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    # Parse and validate
    try:
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        analysis = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        analysis = {
            "developer_vibe": "A passionate developer building cool things.",
            "top_skills": ["Programming", "Open Source", "Problem Solving"],
            "fun_fact": "This developer has been busy shipping code!",
            "card_theme": "builder",
        }

    return json.dumps(analysis)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3: Generate Card HTML
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def generate_card_html(username: str, github_data: str, analysis: str) -> str:
    """
    Generate a beautiful, self-contained HTML dev card.
    Inputs:
      - username: GitHub username
      - github_data: JSON string from scrape_github
      - analysis: JSON string from analyze_profile
    Returns: A complete HTML string for the dev card.
    """
    data = json.loads(github_data)
    profile = json.loads(analysis)

    name = data.get("name", username)
    bio = data.get("bio", "")
    location = data.get("location", "Earth")
    avatar_url = data.get("avatar_url", "")
    public_repos = data.get("public_repos", 0)
    followers = data.get("followers", 0)
    following = data.get("following", 0)
    top_repos = data.get("top_repos", [])[:3]
    top_languages = data.get("top_languages", [])

    vibe = profile.get("developer_vibe", "")
    skills = profile.get("top_skills", [])
    fun_fact = profile.get("fun_fact", "")
    theme = profile.get("card_theme", "builder")

    # Theme-specific styles
    themes = {
        "hacker": {
            "bg": "linear-gradient(135deg, #0a0f0d 0%, #0d1a14 50%, #0a0f0d 100%)",
            "accent": "#00ff41",
            "accent_dim": "#00cc33",
            "text": "#c9d1d9",
            "card_bg": "rgba(13, 26, 20, 0.95)",
            "border": "#00ff4130",
            "badge_bg": "rgba(0, 255, 65, 0.1)",
            "icon": "⚡",
        },
        "builder": {
            "bg": "linear-gradient(135deg, #020b18 0%, #041428 40%, #071e38 70%, #020b18 100%)",
            "accent": "#00d4ff",
            "accent_dim": "#00aacc",
            "text": "#cdd9e5",
            "card_bg": "rgba(4, 16, 32, 0.97)",
            "border": "#00d4ff25",
            "badge_bg": "rgba(0, 212, 255, 0.08)",
            "icon": "🚀",
        },
        "researcher": {
            "bg": "linear-gradient(135deg, #020b18 0%, #041428 40%, #071e38 70%, #020b18 100%)",
            "accent": "#7ee8fa",
            "accent_dim": "#5bc8e0",
            "text": "#cdd9e5",
            "card_bg": "rgba(4, 16, 32, 0.97)",
            "border": "#7ee8fa25",
            "badge_bg": "rgba(126, 232, 250, 0.08)",
            "icon": "🔬",
        },
        "designer": {
            "bg": "linear-gradient(135deg, #1a0a1a 0%, #2d0d2d 50%, #1a0a1a 100%)",
            "accent": "#f778ba",
            "accent_dim": "#d960a0",
            "text": "#c9d1d9",
            "card_bg": "rgba(45, 13, 45, 0.95)",
            "border": "#f778ba30",
            "badge_bg": "rgba(247, 120, 186, 0.1)",
            "icon": "🎨",
        },
        "open-source-hero": {
            "bg": "linear-gradient(135deg, #0f0a1a 0%, #1a0d2d 50%, #0f0a1a 100%)",
            "accent": "#a371f7",
            "accent_dim": "#8b5cf6",
            "text": "#c9d1d9",
            "card_bg": "rgba(26, 13, 45, 0.95)",
            "border": "#a371f730",
            "badge_bg": "rgba(163, 113, 247, 0.1)",
            "icon": "🌟",
        },
    }

    t = themes.get(theme, themes["builder"])

    # Build skills badges HTML
    skills_html = "".join(
        f'<span class="badge">{skill}</span>' for skill in skills
    )

    # Build top repos HTML
    repos_html = ""
    for repo in top_repos:
        lang_dot = f'<span class="lang-dot"></span>{repo["language"]}' if repo.get("language") else ""
        repos_html += f"""
        <div class="repo">
            <div class="repo-header">
                <span class="repo-icon">📁</span>
                <a href="https://github.com/{username}/{repo['name']}" target="_blank" class="repo-name">{repo['name']}</a>
                <span class="stars">⭐ {repo['stars']}</span>
            </div>
            <p class="repo-desc">{repo.get('description', '')[:80]}</p>
            <span class="repo-lang">{lang_dot}</span>
        </div>"""

    # Build languages bar
    total_lang = sum(l["count"] for l in top_languages) if top_languages else 1
    lang_bar_html = ""
    lang_labels_html = ""
    lang_colors = ["#f1e05a", "#3572A5", "#e34c26", "#563d7c", "#b07219",
                    "#00ADD8", "#DA5B0B", "#4F5D95"]
    for i, lang in enumerate(top_languages[:6]):
        pct = (lang["count"] / total_lang) * 100
        color = lang_colors[i % len(lang_colors)]
        lang_bar_html += f'<div style="width:{pct:.1f}%;background:{color};height:100%;"></div>'
        lang_labels_html += f'<span class="lang-label"><span style="background:{color};width:8px;height:8px;border-radius:50%;display:inline-block;margin-right:4px;"></span>{lang["language"]} {pct:.0f}%</span>'

    html = f"""<!DOCTYPE html>
<html lang="en" data-mode="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — Dev Card</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="icon" type="image/png" href="/frontend/favicon.png">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  /* ── Dark mode (default) ── */
  [data-mode="dark"] {{
    --bg: {t['bg']};
    --card-bg: {t['card_bg']};
    --border: {t['border']};
    --accent: {t['accent']};
    --accent-dim: {t['accent_dim']};
    --badge-bg: {t['badge_bg']};
    --text: {t['text']};
    --text-muted: #8b949e;
    --text-heading: #f0f6fc;
    --stat-bg: rgba(255,255,255,0.03);
    --stat-border: rgba(255,255,255,0.06);
    --repo-bg: rgba(255,255,255,0.02);
    --repo-border: rgba(255,255,255,0.06);
    --footer-color: #484f58;
    --section-color: #8b949e;
  }}

  /* ── Light mode ── */
  [data-mode="light"] {{
    --bg: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 50%, #f0f4ff 100%);
    --card-bg: rgba(255,255,255,0.97);
    --border: rgba(99,102,241,0.2);
    --accent: #4f46e5;
    --accent-dim: #3730a3;
    --badge-bg: rgba(79,70,229,0.08);
    --text: #374151;
    --text-muted: #6b7280;
    --text-heading: #111827;
    --stat-bg: rgba(79,70,229,0.04);
    --stat-border: rgba(79,70,229,0.12);
    --repo-bg: rgba(79,70,229,0.03);
    --repo-border: rgba(79,70,229,0.1);
    --footer-color: #9ca3af;
    --section-color: #6b7280;
  }}

  /* ── Neon mode ── */
  [data-mode="neon"] {{
    --bg: linear-gradient(135deg, #000000 0%, #0a0015 50%, #000000 100%);
    --card-bg: rgba(5,0,20,0.97);
    --border: rgba(255,0,255,0.3);
    --accent: #ff00ff;
    --accent-dim: #cc00cc;
    --badge-bg: rgba(255,0,255,0.08);
    --text: #e0d0ff;
    --text-muted: #a080c0;
    --text-heading: #ffffff;
    --stat-bg: rgba(255,0,255,0.05);
    --stat-border: rgba(255,0,255,0.15);
    --repo-bg: rgba(255,0,255,0.03);
    --repo-border: rgba(255,0,255,0.12);
    --footer-color: #6040a0;
    --section-color: #a080c0;
  }}

  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 20px;
    color: var(--text);
    transition: background 0.4s ease;
  }}

  /* ── Theme switcher bar ── */
  .theme-switcher {{
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
    background: rgba(0,0,0,0.3);
    padding: 6px;
    border-radius: 30px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
  }}
  [data-mode="light"] .theme-switcher {{
    background: rgba(255,255,255,0.8);
    border-color: rgba(79,70,229,0.2);
  }}
  .theme-btn {{
    padding: 6px 16px;
    border-radius: 20px;
    border: none;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.25s ease;
    background: transparent;
    color: rgba(255,255,255,0.5);
    letter-spacing: 0.5px;
  }}
  [data-mode="light"] .theme-btn {{ color: rgba(0,0,0,0.4); }}
  .theme-btn:hover {{ color: rgba(255,255,255,0.9); transform: scale(1.05); }}
  [data-mode="light"] .theme-btn:hover {{ color: rgba(0,0,0,0.8); }}
  .theme-btn.active {{
    background: var(--accent);
    color: #fff;
    box-shadow: 0 0 12px var(--accent);
  }}
  [data-mode="light"] .theme-btn.active {{ color: #fff; }}

  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 32px;
    max-width: 440px;
    width: 100%;
    backdrop-filter: blur(20px);
    box-shadow: 0 0 60px color-mix(in srgb, var(--accent) 6%, transparent), 0 20px 60px rgba(0,0,0,0.4);
    position: relative;
    overflow: hidden;
    transition: background 0.4s, border-color 0.4s, box-shadow 0.4s;
  }}
  .card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    transition: background 0.4s;
  }}
  [data-mode="neon"] .card {{
    box-shadow: 0 0 40px rgba(255,0,255,0.15), 0 0 80px rgba(255,0,255,0.05), 0 20px 60px rgba(0,0,0,0.8);
  }}

  .theme-badge {{
    position: absolute;
    top: 16px;
    right: 16px;
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.4s;
  }}
  .header {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }}
  .avatar {{
    width: 72px;
    height: 72px;
    border-radius: 50%;
    border: 2px solid var(--accent);
    box-shadow: 0 0 20px color-mix(in srgb, var(--accent) 20%, transparent);
    object-fit: cover;
    transition: border-color 0.4s, box-shadow 0.4s;
  }}
  [data-mode="neon"] .avatar {{
    box-shadow: 0 0 20px rgba(255,0,255,0.4), 0 0 40px rgba(255,0,255,0.1);
  }}
  .header-info h1 {{
    font-size: 20px;
    font-weight: 700;
    color: var(--text-heading);
    line-height: 1.2;
    transition: color 0.4s;
  }}
  .header-info .username {{
    color: var(--accent);
    font-size: 13px;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    transition: color 0.4s;
  }}
  .header-info .location {{
    color: var(--text-muted);
    font-size: 12px;
    margin-top: 2px;
    transition: color 0.4s;
  }}
  .vibe {{
    background: var(--badge-bg);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    border-radius: 0 10px 10px 0;
    margin-bottom: 20px;
    font-style: italic;
    font-size: 13px;
    color: var(--text);
    line-height: 1.5;
    transition: all 0.4s;
  }}
  .stats {{
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .stat {{
    flex: 1;
    text-align: center;
    background: var(--stat-bg);
    border: 1px solid var(--stat-border);
    border-radius: 12px;
    padding: 12px 8px;
    transition: all 0.4s;
  }}
  .stat-value {{
    font-size: 22px;
    font-weight: 700;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    transition: color 0.4s;
  }}
  [data-mode="neon"] .stat-value {{
    text-shadow: 0 0 10px rgba(255,0,255,0.6);
  }}
  .stat-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--section-color);
    margin-top: 2px;
    transition: color 0.4s;
  }}
  .section-title {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--section-color);
    margin-bottom: 10px;
    font-weight: 600;
    transition: color 0.4s;
  }}
  .badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
  }}
  .badge {{
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--accent);
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.4s;
  }}
  [data-mode="neon"] .badge {{
    box-shadow: 0 0 8px rgba(255,0,255,0.2);
  }}
  .repo {{
    background: var(--repo-bg);
    border: 1px solid var(--repo-border);
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
    transition: all 0.25s;
  }}
  .repo:hover {{ border-color: var(--accent); }}
  [data-mode="neon"] .repo:hover {{ box-shadow: 0 0 12px rgba(255,0,255,0.2); }}
  .repo-header {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }}
  .repo-icon {{ font-size: 14px; }}
  .repo-name {{
    color: var(--accent);
    text-decoration: none;
    font-weight: 600;
    font-size: 13px;
    transition: color 0.4s;
  }}
  .repo-name:hover {{ text-decoration: underline; }}
  .stars {{
    margin-left: auto;
    font-size: 12px;
    color: var(--text-muted);
    transition: color 0.4s;
  }}
  .repo-desc {{
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.4;
    margin-bottom: 4px;
    transition: color 0.4s;
  }}
  .repo-lang {{
    font-size: 11px;
    color: var(--text-muted);
    transition: color 0.4s;
  }}
  .lang-dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--accent);
    display: inline-block;
    margin-right: 4px;
    vertical-align: middle;
    transition: background 0.4s;
  }}
  .lang-bar {{
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 8px;
    background: rgba(128,128,128,0.1);
  }}
  .lang-labels {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 20px;
  }}
  .lang-label {{
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    transition: color 0.4s;
  }}
  .fun-fact {{
    background: var(--repo-bg);
    border: 1px solid var(--repo-border);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.5;
    transition: all 0.4s;
  }}
  .fun-fact strong {{ color: var(--accent); transition: color 0.4s; }}
  .footer {{
    text-align: center;
    margin-top: 20px;
    padding-top: 16px;
    border-top: 1px solid var(--repo-border);
    font-size: 11px;
    color: var(--footer-color);
    font-family: 'JetBrains Mono', monospace;
    transition: all 0.4s;
  }}
  .footer a {{ color: var(--accent-dim); text-decoration: none; transition: color 0.4s; }}
</style>
</head>
<body>

<div class="theme-switcher">
  <button class="theme-btn active" onclick="setMode('dark')" id="btn-dark">🌙 Dark</button>
  <button class="theme-btn" onclick="setMode('light')" id="btn-light">☀️ Light</button>
  <button class="theme-btn" onclick="setMode('neon')" id="btn-neon">⚡ Neon</button>
</div>

<div class="card">
  <span class="theme-badge">{t['icon']} {theme}</span>
  <div class="header">
    <img class="avatar" src="{avatar_url}" alt="{name}" />
    <div class="header-info">
      <h1>{name}</h1>
      <div class="username">@{username}</div>
      <div class="location">📍 {location}</div>
    </div>
  </div>

  <div class="vibe">"{vibe}"</div>

  <div class="stats">
    <div class="stat">
      <div class="stat-value">{public_repos}</div>
      <div class="stat-label">Repos</div>
    </div>
    <div class="stat">
      <div class="stat-value">{followers}</div>
      <div class="stat-label">Followers</div>
    </div>
    <div class="stat">
      <div class="stat-value">{following}</div>
      <div class="stat-label">Following</div>
    </div>
  </div>

  <div class="section-title">Top Skills</div>
  <div class="badges">{skills_html}</div>

  <div class="section-title">Languages</div>
  <div class="lang-bar">{lang_bar_html}</div>
  <div class="lang-labels">{lang_labels_html}</div>

  <div class="section-title">Top Repositories</div>
  {repos_html}

  <div class="fun-fact">
    <strong>💡 Fun fact:</strong> {fun_fact}
  </div>

  <div class="footer">
    Generated by <a href="#">GitHub Dev Card Generator</a>
  </div>
</div>

<script>
  function setMode(mode) {{
    document.documentElement.setAttribute('data-mode', mode);
    document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-' + mode).classList.add('active');
  }}
</script>

</body>
</html>"""

    return html


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4: Save Card
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def save_card(username: str, html: str) -> str:
    """
    Save the generated HTML dev card to disk.
    Input: username and the HTML string from generate_card_html.
    Returns: the relative URL path to the saved card.
    """
    cards_dir = pathlib.Path(__file__).parent.parent / "frontend" / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)

    filepath = cards_dir / f"{username}.html"
    filepath.write_text(html, encoding="utf-8")

    return f"/card/{username}"


# ─────────────────────────────────────────────────────────────────────────────
# Run server
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
