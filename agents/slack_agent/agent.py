import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import asyncio
from agents.slack_agent.utils.slack_app import app, get_or_create_session, delete_messages

def get_message_tool(msg: str) -> dict:
    """Tool to handle specific user queries."""
    if not isinstance(msg, str):
        return {"status": "error", "error_message": "Invalid input: msg must be a string."}
    normalized_msg = msg.lower().strip()
    if normalized_msg.startswith("hello") or "hi" in normalized_msg:
        return {"status": "success", "report": "Hey there! How can I assist you today?..."}
    match normalized_msg:
        case "time":
            now = datetime.datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")
            return {"status": "success", "report": f"The current time in UTC is {now}."}
        case "info":
            return {"status": "success", "report": "You are Shivam, a software engineer..."}
        case "clear":
            return {"status": "success", "report": "Initiating message deletion..."}
        case "help":
            return {"status": "success", "report": "Available commands: hello, time, info, clear, help."}
        case _:
            return {"status": "error", "error_message": f"No info for '{msg}'."}

root_agent = Agent(
    name="slack_agent",
    model="gemini-2.0-flash",
    instruction="Use get_message_tool to answer greetings, time, info, or clear requests.",
    description="Slack‐friendly agent",
    tools=[get_message_tool],
)

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="slack_agent"
)

# Map Slack user IDs to ADK session IDs
user_to_session_mapping = {}  # slack_user_id -> adk_session_id

# ─── Bolt setup ───────────────────────────────────────

async def run_in_executor(runner, user_id, session_id, content):
    """Run synchronous runner.run in an executor to avoid blocking."""
    loop = asyncio.get_event_loop()
    def sync_run():
        final_response = "Sorry, I couldn't process that."
        tool_response = None
        for event_obj in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=content
        ):
            if not event_obj.content:
                continue
            parts = getattr(event_obj.content, "parts", [])
            for part in parts:
                if isinstance(part, types.Part):
                    if hasattr(part, "function_call") and part.function_call:
                        print(f"Function call detected: {part.function_call}")
                        func_name = getattr(part.function_call, "name", None)
                        func_args = getattr(part.function_call, "args", {})
                        if func_name is not None and func_name == "get_message_tool" and "msg" in func_args:
                            tool_response = get_message_tool(func_args["msg"])
                            print(f"Tool response: {tool_response}")
                    elif hasattr(part, "function_response") and part.function_response:
                        response_data = getattr(part.function_response, "response", None)
                        if response_data and isinstance(response_data, dict):
                            tool_response = response_data
                    elif hasattr(part, "text") and part.text:
                        final_response = part.text
            if tool_response:
                final_response = (tool_response.get("report", final_response)
                                  if tool_response.get("status") == "success"
                                  else tool_response.get("error_message", final_response))
        return final_response
    return await loop.run_in_executor(None, sync_run)

# @app.event("message")
# async def handle_message(event, say):
#     """Handle incoming Slack messages asynchronously."""
#     user_id = event.get("user")
#     text = event.get("text", "").strip()
#     channel_id = event.get("channel")

#     # Skip if no user ID or text, or if it's a bot message
#     if not user_id or not text or event.get("bot_id"):
#         return

#     try:
#         session_id = await get_or_create_session(user_id)
#         content = types.Content(role="user", parts=[types.Part(text=text)])

#         # Run synchronous runner.run in an executor
#         final_response = await run_in_executor(runner, user_id, session_id, content)
        
#         # If the "clear" command is detected, delete messages
#         if text.lower().strip() == "clear":
#             auth_response = await app.client.auth_test()
#             bot_user_id = auth_response.get("user_id")
#             if not bot_user_id:
#                 await say("Error: Could not retrieve bot user ID.")
#                 return
#             delete_result = await delete_messages(channel_id, user_id, bot_user_id)
#             await say(f"{final_response} {delete_result}")
#         else:
#             await say(final_response)

#     except Exception as e:
#         print(f"Error running agent: {e}")
#         await say("Sorry, I encountered an error processing your request.")