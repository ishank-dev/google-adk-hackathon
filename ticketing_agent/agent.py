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
from multi_tool_agent_llama.multi_tool_agent.rag_kb_llm import chat

# Fallback patterns for unknown answers
FALLBACK_PATTERNS = [
    r"an error occured",
    r"i don'?t know",
    r"i'?m not sure",
    r"(could|can)('?t| not) find",
    r"no relevant",
]

async def find_or_create_faq_channel(client) -> str:
    """
    Ensure a public channel named 'faq' exists, returning its channel ID.
    """
    resp = await client.conversations_list(types="public_channel", limit=1000)
    for ch in resp.get("channels", []):
        if ch.get("name") == "faq":
            return ch["id"]
    resp = await client.conversations_create(name="faq", is_private=False)
    return resp["channel"]["id"]

async def post_question_to_faq(client, faq_ch: str, question: str, user_id: str) -> Optional[str]:
    """
    Post the unanswered question to the #faq channel thread.
    """
    resp = await client.chat_postMessage(
        channel=faq_ch,
        text=(
            f":triangular_flag_on_post: <@{user_id}> asked:\n> {question}\n\n"
            "_Helping hands, please reply in this thread if you’ve solved it!_"
        )
    )
    return resp.get("ts")

async def get_answer(question: str, user_id: str, client) -> Dict[str, str]:
    """
    Query the LLM and fall back to posting in #faq if needed.
    """
    try:
        answer = chat(question, llm=llm)
        lower = answer.lower()
        # if fallback pattern matches, log to #faq
        if any(re.search(p, lower) for p in FALLBACK_PATTERNS):
            faq_ch = await find_or_create_faq_channel(client)
            await post_question_to_faq(client, faq_ch, question, user_id)
            return {
                "status": "error",
                "error_message": (
                    "I'm sorry, I don't have an answer right now. "
                    "I've posted your question in #faq—please check there."
                )
            }
        return {"status": "success", "message": answer}
    except Exception as e:
        print(f"Error getting answer: {e}")
        return {"status": "error", "error_message": "Internal error, please try again later."}

# Synchronous wrapper (runs in separate thread)
def get_answer_sync(question: str, user_id: str, client) -> Dict[str, str]:
    return asyncio.run(get_answer(question, user_id, client))

# Tool exposed to the ADK agent
def get_answer_tool(question: str) -> Dict[str, str]:
    # session_service ensures valid session; auth is handled upstream
    try:
        # retrieve user_id and client from context (captured in executor)
        user_id = types.Part  # placeholder to satisfy type inference
        return get_answer_sync(question, current_user, current_client)
    except NameError:
        return {"status": "error", "error_message": "Authorization error: use this from Slack."}

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
