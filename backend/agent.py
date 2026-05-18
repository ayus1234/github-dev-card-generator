"""
Pipeline orchestrator for Dev Card Generator.
Replaces Google ADK with a direct Groq-powered pipeline.
Steps: scrape → analyze → generate_html → save
"""

import os
import pathlib
from dotenv import load_dotenv

load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# Import the MCP tool functions directly (no subprocess needed)
from mcp_server import (
    scrape_github,
    scrape_gitlab,
    scrape_linkedin,
    analyze_profile,
    generate_card_html,
    save_card,
)


def run_pipeline(
    username: str,
    platform: str = "github",
    theme_override: str = "auto",
    layout: str = "standard",
) -> dict:
    """
    Run the full card generation pipeline synchronously with caching.
    Returns dict with keys: username, card_url, message
    """
    import json
    
    # Establish local profile cache directory
    cache_dir = pathlib.Path(__file__).parent.parent / "frontend" / "cards" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{username.lower().strip()}_{platform}.json"

    raw_data = None
    if cache_file.exists():
        try:
            raw_data = cache_file.read_text(encoding="utf-8")
        except Exception:
            pass

    if not raw_data:
        # Step 1: Scrape profile (since no cache is present)
        if platform == "gitlab":
            raw_data = scrape_gitlab(username)
        elif platform == "linkedin":
            raw_data = scrape_linkedin(username)
        else:
            raw_data = scrape_github(username)

        # Cache the result if it's a valid profile scrape (no error and not a mock fallback)
        try:
            parsed = json.loads(raw_data)
            if "error" not in parsed:
                # Do not cache mock fallbacks if they haven't set their key yet
                is_mock = "update this card once connected to the API" in parsed.get("bio", "")
                if not is_mock:
                    cache_file.write_text(raw_data, encoding="utf-8")
        except Exception:
            pass

    # Check for scrape errors
    data = json.loads(raw_data)
    if "error" in data:
        raise ValueError(data["error"])

    # Step 2: Analyze profile with Groq
    analysis = analyze_profile(raw_data)

    # Step 3: Generate HTML card
    html = generate_card_html(
        username=username,
        github_data=raw_data,
        analysis=analysis,
        theme_override=theme_override,
        layout=layout,
    )

    # Step 4: Save card to disk
    result = save_card(username, html)
    saved = json.loads(result)

    platform_labels = {"gitlab": "GitLab", "linkedin": "LinkedIn"}
    label = platform_labels.get(platform, "GitHub")

    return {
        "username": username,
        "card_url": saved["url"],
        "message": f"Dev card generated for {label} user {username}!",
    }
