"""
Quick test for the Groq-powered card generation pipeline.
Run with: python test_agent.py
"""

from agent import run_pipeline


def main():
    print("Testing card generation pipeline with Groq...\n")
    result = run_pipeline(
        username="torvalds",
        platform="github",
        theme_override="auto",
        layout="standard",
    )
    print(f"Username : {result['username']}")
    print(f"Card URL : {result['card_url']}")
    print(f"Message  : {result['message']}")


if __name__ == "__main__":
    main()
