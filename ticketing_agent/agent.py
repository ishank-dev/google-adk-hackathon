import asyncio
import re
from typing import Optional, Dict
from slack_bolt.async_app import AsyncApp
from slack_sdk.errors import SlackApiError
from google.adk.sessions import InMemorySessionService
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types
from slack_agent.utils.llm import llm
from slack_agent.utils.slack_app import (
    app,
    get_or_create_session,
    delete_messages,
    session_service
)
from ticketing_agent.modules.answers import get_answer


# Synchronous wrapper (runs in separate thread)
def get_answer_sync(question: str, user_id: str, client) -> Dict[str, str]:
    return asyncio.run(get_answer(question, user_id, client))

# Tool exposed to the ADK agent
async def get_answer_tool(question: str) -> Dict[str, str]:
    try:
        # current_user / current_client already set in globals
        return await get_answer(question, current_user, current_client)
    except NameError:
        return {"status": "error", "error_message": "Auth error: call me from Slack."}

# Build the ADK agent
root_agent = Agent(
    name="slack_agent",
    model="gemini-2.0-flash",
    instruction="Use get_answer_tool to answer Slack user questions; do not hallucinate.",
    description="Slack Q&A Bot",
    tools=[get_answer_tool],
)

# Shared session store & runner
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="slack_agent",
)

# Helper to run agent in thread pool
async def run_in_executor(
    runner: Runner,
    user_id: str,
    session_id: str,
    content: types.Content,
    client
) -> str:
    loop = asyncio.get_event_loop()

    def sync_run() -> str:
        final = "Sorry, I couldn't process that."
        try:
            # seed globals before running
            global current_user, current_client
            current_user, current_client = user_id, client

            for ev in runner.run(user_id=user_id, session_id=session_id, new_message=content):
                if not ev.content or not ev.content.parts:
                    continue
                for part in ev.content.parts:
                    if hasattr(part, "function_response") and part.function_response:
                        resp = part.function_response.response
                        if not resp:
                            continue
                        if resp.get("status") == "success":
                            final = resp.get("message", final)
                        else:
                            final = resp.get("error_message", final)
                    elif hasattr(part, "text") and part.text:
                        final = part.text
        except Exception:
            import traceback; traceback.print_exc()
            final = "Oops—an error occurred inside the agent."
        return final

    return await loop.run_in_executor(None, sync_run)

# Slack event handler
@app.event("message")
async def handle_message(event, say):
    user_id = event.get("user")
    text = (event.get("text") or "").strip()
    channel_id = event.get("channel")
    [identifier, command] = text.split(" ") if " " in text else (text, "")
    if identifier != "ivk":
        # Do nothing
        return
    text = command
    # create or fetch session
    try:
        session = await get_or_create_session(user_id)
        session_id = session
    except Exception as e:
        print(f"Session error: {e}")
        await say("Could not start session. Try again later.")
        return

    content = types.Content(role="user", parts=[types.Part(text=text)])
    result = await run_in_executor(runner, user_id, session_id, content, app.client)

    if text.lower() == "clear":
        try:
            auth = await app.client.auth_test()
            bot_id = auth.get("user_id") or ""
            deleted = await delete_messages(channel_id, user_id, bot_id)
            await say(f"{result} {deleted}")
        except SlackApiError as e:
            await say(f"Error clearing messages: {e.response['error']}")
    else:
        await say(result)
