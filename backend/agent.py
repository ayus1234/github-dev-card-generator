"""
ADK Agent definition for GitHub Dev Card Generator.
Connects to the MCP server and orchestrates the 4-tool pipeline.
"""

import os
import sys
import pathlib
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
from mcp import StdioServerParameters

# Load .env relative to this file so it works regardless of cwd
load_dotenv(dotenv_path=pathlib.Path(__file__).parent / ".env")

# Path to the MCP server script (same directory)
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

# System instruction enforcing the 4-step pipeline
SYSTEM_INSTRUCTION = """You are a GitHub profile analyst and dev card generator.

When a user gives you a GitHub username, you ALWAYS follow this exact sequence:

1. First, call scrape_github with the username to fetch their GitHub profile data.
2. Then, call analyze_profile with the JSON string result from step 1.
3. Then, call generate_card_html with the username, the github_data JSON string from step 1, and the analysis JSON string from step 2.
4. Finally, call save_card with the username and the HTML string from step 3.

CRITICAL RULES:
- Never skip steps. Always execute all 4 steps in order.
- Pass results between tools as strings (they are JSON strings).
- Be enthusiastic about developers' work in your responses.
- If the profile is private or doesn't exist, say so clearly and do not proceed further.
- After completing all steps, respond with the card URL and a brief celebration of the developer's profile.
- Include the card URL path from save_card in your final response.
"""

def get_agent():
    """Create and return the GitHub card agent with MCP tools."""
    # Pass environment variables to the MCP subprocess
    # The subprocess doesn't inherit .env, so we forward the key explicitly
    env = {**os.environ}
    if os.getenv("GEMINI_API_KEY"):
        env["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
    if os.getenv("GITHUB_TOKEN"):
        env["GITHUB_TOKEN"] = os.getenv("GITHUB_TOKEN")

    mcp_toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=sys.executable,
                args=[MCP_SERVER_PATH],
                env=env,
            ),
            timeout=120.0,  # Allow up to 2 min for Gemini tool calls
        )
    )

    github_card_agent = Agent(
        model="gemini-2.0-flash-lite",
        name="github_card_agent",
        instruction=SYSTEM_INSTRUCTION,
        tools=[mcp_toolset],
    )

    return github_card_agent

# Export the agent
github_card_agent = get_agent()
