"""
MCP Server for Dev Card Generator.
Exposes tools via FastMCP:
  1. scrape_github   — fetch public GitHub profile data
  2. analyze_profile — AI-powered profile analysis via Groq (Llama)
  3. generate_card_html — render a themed HTML dev card
  4. save_card       — persist the card to disk
"""

import os
import json
import pathlib
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from groq import Groq

# Load .env relative to this file so it works regardless of cwd
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# ── Groq client setup ────────────────────────────────────────────────────────
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please set it in your environment or .env file.")
    return Groq(api_key=api_key)

GROQ_MODEL = "llama-3.3-70b-versatile"

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
    Analyze a developer's profile using Groq (Llama).
    Input: JSON string of github profile data from scrape_github.
    Returns JSON with: developer_vibe, top_skills, fun_fact, card_theme.
    card_theme is one of: hacker, builder, researcher, designer, open-source-hero.
    """
    # Safe strip of massive base64 strings (like avatar_url) to avoid token context limits
    try:
        data_clean = json.loads(github_data)
        if "avatar_url" in data_clean:
            data_clean["avatar_url"] = "[avatar_image_data_embedded]"
        github_data_clean = json.dumps(data_clean, indent=2)
    except Exception:
        github_data_clean = github_data

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
{github_data_clean}

Respond with ONLY valid JSON, no markdown, no code fences."""

    response = get_groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=512,
    )
    text = response.choices[0].message.content.strip()

    # Parse and validate
    try:
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
def scrape_gitlab(username: str) -> str:
    """
    Fetch public GitLab profile data for a given username.
    Returns JSON with: name, bio, location, public_repos, followers,
    avatar_url, top 6 projects (name, stars, language, description),
    and aggregated language stats.
    """
    headers = {"Accept": "application/json"}
    gitlab_token = os.getenv("GITLAB_TOKEN")
    if gitlab_token:
        headers["PRIVATE-TOKEN"] = gitlab_token

    with httpx.Client(timeout=30) as client:
        # Search for user
        search_resp = client.get(
            f"https://gitlab.com/api/v4/users",
            params={"username": username},
            headers=headers,
        )
        search_resp.raise_for_status()
        users = search_resp.json()
        if not users:
            return json.dumps({"error": f"GitLab user '{username}' not found."})
        user = users[0]
        user_id = user["id"]

        # Fetch projects
        projects_resp = client.get(
            f"https://gitlab.com/api/v4/users/{user_id}/projects",
            params={"order_by": "star_count", "sort": "desc", "per_page": 30},
            headers=headers,
        )
        projects_resp.raise_for_status()
        projects = projects_resp.json()

    top_repos = [
        {
            "name": p["name"],
            "stars": p.get("star_count", 0),
            "language": p.get("language"),
            "description": p.get("description") or "",
        }
        for p in projects[:6]
    ]

    lang_count: dict[str, int] = {}
    for p in projects:
        lang = p.get("language")
        if lang:
            lang_count[lang] = lang_count.get(lang, 0) + 1
    top_languages = sorted(lang_count.items(), key=lambda x: x[1], reverse=True)[:8]

    result = {
        "username": username,
        "name": user.get("name") or username,
        "bio": user.get("bio") or "",
        "location": user.get("location") or "Earth",
        "avatar_url": user.get("avatar_url", ""),
        "public_repos": len(projects),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "top_repos": top_repos,
        "top_languages": [{"language": lang, "count": cnt} for lang, cnt in top_languages],
        "platform": "gitlab",
    }
    return json.dumps(result)


def url_to_base64_img(url: str) -> str:
    """Download an image from a URL and convert it to a base64 Data URL to prevent hotlinking issues."""
    if not url:
        return ""
    if url.startswith("data:image/"):
        return url
    try:
        import base64
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "image/jpeg")
                if "image" not in content_type:
                    content_type = "image/jpeg"
                encoded = base64.b64encode(resp.content).decode("utf-8")
                return f"data:{content_type};base64,{encoded}"
    except Exception:
        pass
    return url


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5: Scrape LinkedIn (mock — LinkedIn blocks API scraping without paid plan)
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def scrape_linkedin(username: str) -> str:
    """
    Fetch LinkedIn profile data for a given username/profile ID.
    Supports:
      1. Apify API (set APIFY_API_TOKEN in .env) using harvestapi/linkedin-profile-scraper (No Cookies).
      2. Proxycurl API (set PROXYCURL_API_KEY in .env) for real, complete profile data.
      3. Official LinkedIn API (set LINKEDIN_TOKEN in .env) for token owner only.
      4. Graceful Mock fallback if no API keys are provided.
    """
    # ── Option 1: Apify (harvestapi/linkedin-profile-scraper) ──────────────────────
    apify_token = os.getenv("APIFY_API_TOKEN", "")
    if apify_token:
        try:
            # Construct the target LinkedIn profile URL
            profile_url = username
            if not (profile_url.startswith("http://") or profile_url.startswith("https://")):
                profile_url = f"https://www.linkedin.com/in/{username}"
            
            # API endpoint to run the actor synchronously and directly get dataset items
            url = f"https://api.apify.com/v2/acts/harvestapi~linkedin-profile-scraper/run-sync-get-dataset-items?token={apify_token}&timeout=60"
            
            headers = {"Content-Type": "application/json"}
            payload = {
                "urls": [profile_url],
                "profileUrls": [profile_url],
                "profileScraperMode": "Profile details no email ($4 per 1k)"
            }
            
            with httpx.Client(timeout=65) as client:
                resp = client.post(url, json=payload, headers=headers)
                
                if resp.status_code in (200, 201):
                    items = resp.json()
                    if isinstance(items, list) and len(items) > 0:
                        data = items[0]
                        
                        # Resilient mapping of keys (supporting camelCase, snake_case, etc.)
                        name = (
                            data.get("fullName")
                            or data.get("full_name")
                            or f"{data.get('firstName', '')} {data.get('lastName', '')}".strip()
                            or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
                            or username
                        )
                        
                        bio = data.get("headline") or data.get("occupation") or "Professional on LinkedIn"
                        summary = data.get("summary") or data.get("about")
                        if summary:
                            bio += f" | {summary[:150]}..."
                            
                        # Extract Location
                        location_data = data.get("location") or "Global"
                        if isinstance(location_data, dict):
                            location = location_data.get("name") or ", ".join(filter(None, [location_data.get("city"), location_data.get("country")])) or "Global"
                        else:
                            location = str(location_data)
                            
                        # Extract Skills
                        raw_skills = data.get("skills", [])
                        skills_list = []
                        for s in raw_skills:
                            if isinstance(s, dict):
                                name_val = s.get("name") or s.get("title")
                                if name_val:
                                    skills_list.append(name_val)
                            elif isinstance(s, str):
                                skills_list.append(s)
                        skills_list = skills_list[:5]
                        top_skills = [{"language": s, "count": 1} for s in skills_list] if skills_list else [{"language": "Professional Skills", "count": 1}]
                        
                        # Extract Experiences
                        raw_experiences = data.get("experiences") or data.get("experience") or []
                        top_repos = []
                        for exp in raw_experiences[:3]:
                            if isinstance(exp, dict):
                                company = exp.get("companyName") or exp.get("company_name") or exp.get("company") or "Company"
                                title = exp.get("title") or exp.get("role") or "Role"
                                desc = exp.get("description") or f"{title} at {company}"
                                top_repos.append({
                                    "name": f"{title} @ {company}",
                                    "stars": 0,
                                    "language": "Work Experience",
                                    "description": desc[:100] + "..." if len(desc) > 100 else desc,
                                })
                                
                        # Resilient extraction of the avatar URL
                        avatar_url = ""
                        # Try photo first (which is a string)
                        if data.get("photo") and isinstance(data.get("photo"), str):
                            avatar_url = data.get("photo")
                        # Try profilePicture next (could be dict or string)
                        elif data.get("profilePicture"):
                            prof_pic = data.get("profilePicture")
                            if isinstance(prof_pic, dict):
                                avatar_url = prof_pic.get("url") or prof_pic.get("imageUrl") or ""
                            elif isinstance(prof_pic, str):
                                avatar_url = prof_pic
                        # Fallback to other variants
                        if not avatar_url:
                            avatar_url = (
                                data.get("profile_pic_url")
                                or data.get("profilePhoto")
                                or data.get("avatar_url")
                                or ""
                            )
                        
                        # Convert to base64 to bypass hotlink block & expire issues!
                        if avatar_url and not avatar_url.startswith("data:"):
                            avatar_url = url_to_base64_img(avatar_url)
                            
                        if not avatar_url:
                            avatar_url = f"https://ui-avatars.com/api/?name={name}&background=0A66C2&color=fff&size=200"
                        
                        result = {
                            "username": username,
                            "name": name,
                            "bio": bio,
                            "location": location,
                            "avatar_url": avatar_url,
                            "public_repos": len(raw_experiences),
                            "followers": data.get("connectionsCount") or data.get("connections") or 500,
                            "following": 0,
                            "top_repos": top_repos,
                            "top_languages": top_skills,
                            "platform": "linkedin",
                        }
                        return json.dumps(result)
        except Exception:
            pass

    # ── Option 2: Proxycurl API ───────────────────────────────────────────────────
    proxycurl_key = os.getenv("PROXYCURL_API_KEY", "")
    if proxycurl_key:
        try:
            # Construct the target LinkedIn profile URL
            profile_url = username
            if not (profile_url.startswith("http://") or profile_url.startswith("https://")):
                profile_url = f"https://www.linkedin.com/in/{username}"
            
            headers = {"Authorization": f"Bearer {proxycurl_key}"}
            with httpx.Client(timeout=30) as client:
                resp = client.get(
                    "https://nubela.co/proxycurl/api/v2/linkedin",
                    params={"url": profile_url, "fallback_to_cache": "on-error"},
                    headers=headers,
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # 1. Format Name and Bio
                    name = data.get("full_name") or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or username
                    bio = data.get("headline") or data.get("occupation") or "Professional on LinkedIn"
                    if data.get("summary"):
                        bio += f" | {data['summary'][:150]}..."
                    
                    # 2. Extract Location
                    location = ", ".join(filter(None, [data.get("city"), data.get("state"), data.get("country_full_name")])) or "Global"
                    
                    # 3. Convert LinkedIn Skills to Card Languages/Skills
                    skills_list = [s.get("name") for s in data.get("skills", []) if s.get("name")][:5]
                    top_skills = [{"language": s, "count": 1} for s in skills_list] if skills_list else [{"language": "Professional Skills", "count": 1}]
                    
                    # 4. Map LinkedIn Work Experience to "Top Projects" (so the card visualizes them beautifully)
                    top_repos = []
                    for exp in data.get("experiences", [])[:3]:
                        company = exp.get("company", "Company")
                        title = exp.get("title", "Role")
                        desc = exp.get("description", "") or f"{title} at {company}"
                        top_repos.append({
                            "name": f"{title} @ {company}",
                            "stars": 0,
                            "language": "Work Experience",
                            "description": desc[:100] + "..." if len(desc) > 100 else desc,
                        })
                    
                    avatar_url = data.get("profile_pic_url") or ""
                    if avatar_url and not avatar_url.startswith("data:"):
                        avatar_url = url_to_base64_img(avatar_url)
                    if not avatar_url:
                        avatar_url = f"https://ui-avatars.com/api/?name={name}&background=0A66C2&color=fff&size=200"

                    result = {
                        "username": username,
                        "name": name,
                        "bio": bio,
                        "location": location,
                        "avatar_url": avatar_url,
                        "public_repos": len(data.get("experiences", [])),
                        "followers": data.get("connections", 500),
                        "following": 0,
                        "top_repos": top_repos,
                        "top_languages": top_skills,
                        "platform": "linkedin",
                    }
                    return json.dumps(result)
        except Exception:
            pass

    # ── Option 3: Official LinkedIn API fallback (token owner only) ───────────────
    linkedin_token = os.getenv("LINKEDIN_TOKEN", "")
    if linkedin_token:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    "https://api.linkedin.com/v2/me",
                    headers={
                        "Authorization": f"Bearer {linkedin_token}",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                )
                if resp.status_code == 200:
                    user = resp.json()
                    name = f"{user.get('localizedFirstName', '')} {user.get('localizedLastName', '')}".strip() or username
                    result = {
                        "username": username,
                        "name": name,
                        "bio": user.get("localizedHeadline", "Professional on LinkedIn"),
                        "location": "",
                        "avatar_url": "",
                        "public_repos": 0,
                        "followers": 0,
                        "following": 0,
                        "top_repos": [],
                        "top_languages": [],
                        "platform": "linkedin",
                    }
                    return json.dumps(result)
        except Exception:
            pass

    # ── Option 4: Graceful fallback mock if no keys are configured ─────────────────
    result = {
        "username": username,
        "name": username.replace("-", " ").replace("_", " ").title(),
        "bio": "Professional on LinkedIn — update this card once connected to the API.",
        "location": "Global",
        "avatar_url": f"https://ui-avatars.com/api/?name={username}&background=0A66C2&color=fff&size=200",
        "public_repos": 0,
        "followers": 500,
        "following": 0,
        "top_repos": [],
        "top_languages": [{"language": "Professional Skills", "count": 1}],
        "platform": "linkedin",
    }
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 6: Generate Card HTML
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool
def generate_card_html(username: str, github_data: str, analysis: str, theme_override: str = "auto", layout: str = "standard") -> str:
    """
    Generate a beautiful, self-contained HTML dev card.
    Inputs:
      - username: GitHub/GitLab/Bitbucket username
      - github_data: JSON string from scrape_github, scrape_gitlab, or scrape_bitbucket
      - analysis: JSON string from analyze_profile
      - theme_override: "auto" lets AI pick; else one of dark/light/neon/hacker/builder/researcher/designer/open-source-hero
      - layout: "standard" | "compact" | "wide"
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
    platform = data.get("platform", "github")
    theme = theme_override if theme_override != "auto" else profile.get("card_theme", "builder")

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
        domain = f"{platform}.com"
        repos_html += f"""
        <div class="repo">
            <div class="repo-header">
                <span class="repo-icon">📁</span>
                <a href="https://{domain}/{username}/{repo['name']}" target="_blank" class="repo-name">{repo['name']}</a>
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

    # Layout-specific tweaks
    card_max_width = "440px" if layout == "standard" else ("340px" if layout == "compact" else "680px")
    avatar_size = "72px" if layout != "compact" else "52px"
    card_padding = "32px" if layout != "compact" else "20px"
    repos_to_show = top_repos if layout != "compact" else top_repos[:2]

    # Rebuild repos_html with possibly fewer repos
    repos_html = ""
    for repo in repos_to_show:
        lang_dot = f'<span class="lang-dot"></span>{repo["language"]}' if repo.get("language") else ""
        domain = f"{platform}.com"
        repos_html += f"""
        <div class="repo">
            <div class="repo-header">
                <span class="repo-icon">📁</span>
                <a href="https://{domain}/{username}/{repo['name']}" target="_blank" class="repo-name">{repo['name']}</a>
                <span class="stars">⭐ {repo['stars']}</span>
            </div>
            <p class="repo-desc">{repo.get('description', '')[:80]}</p>
            <span class="repo-lang">{lang_dot}</span>
        </div>"""

    if platform == 'gitlab':
        platform_badge = '🦊 GitLab'
    elif platform == 'linkedin':
        platform_badge = '💼 LinkedIn'
    else:
        platform_badge = '🐙 GitHub'

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
    padding: {card_padding};
    max-width: {card_max_width};
    width: 100%;
    backdrop-filter: blur(20px);
    box-shadow: 0 0 60px rgba(0,0,0,0.15), 0 20px 60px rgba(0,0,0,0.4);
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
  .platform-badge {{
    position: absolute;
    top: 16px;
    left: 16px;
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 10px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 20px;
    letter-spacing: 0.5px;
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
    width: {avatar_size};
    height: {avatar_size};
    border-radius: 50%;
    border: 2px solid var(--accent);
    box-shadow: 0 0 20px rgba(0,0,0,0.3);
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
  <span class="platform-badge">{platform_badge}</span>
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
    Generated by <a href="#">GitHub Dev Card Generator</a> &nbsp;•&nbsp;
    <span id="view-count" style="color:var(--accent)">👁️ —</span> views
  </div>
</div>

<script>
  function setMode(mode) {{
    document.documentElement.setAttribute('data-mode', mode);
    document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('btn-' + mode).classList.add('active');
  }}
  // Load view count
  fetch('/analytics/{username}').then(r=>r.json()).then(d=>{{
    const el = document.getElementById('view-count');
    if(el && d.views !== undefined) el.textContent = '👁️ ' + d.views;
  }}).catch(()=>{{}});
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

    return json.dumps({"url": f"/card/{username}", "username": username})


# ─────────────────────────────────────────────────────────────────────────────
# Run server
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
