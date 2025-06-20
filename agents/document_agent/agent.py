import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent

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
        

def post_document_to_corpus() -> dict:
    """Tool to post a document to the corpus."""
    # This function would typically handle the logic to post a document to the knowledge base.
    # For now, we return a success message.
    return {"status": "success", "report": "Document posted to corpus successfully."}

root_agent = Agent(
    name="document_agent",
    model="gemini-2.0-flash",
    instruction="Use get_message_tool to answer greetings, time, info, or clear requests.",
    description="Slack‐friendly agent",
    tools=[get_message_tool],
)

