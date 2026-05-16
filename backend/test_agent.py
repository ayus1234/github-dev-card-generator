import asyncio
from agent import get_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main():
    agent = get_agent()
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, app_name="test", session_service=session_service)
    
    session = await session_service.create_session(app_name="test", user_id="u1", session_id="s1")
    
    message = types.Content(role="user", parts=[types.Part(text="Generate a dev card for GitHub user: ayus1234")])
    
    try:
        async for event in runner.run_async(user_id="u1", session_id="s1", new_message=message):
            print("EVENT:", event)
    except Exception as e:
        print("EXCEPTION:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
