# main.py
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import uvicorn
import asyncio, shlex, argparse
from fastapi import Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from agents.ticketing_agent.agent import app as slack_bolt_app
from google.adk.cli.fast_api import get_fast_api_app
from agents.ticketing_agent.modules.answers import get_answer
app = get_fast_api_app(
    agents_dir="agents",    # where your `root_agent` modules live
    web=True,               # serve the UI at "/"
)

slack_handler = AsyncSlackRequestHandler(slack_bolt_app)


@slack_bolt_app.command("/ask_illa")
async def handle_ask_illa(ack, body, respond):
    text = body.get("text", "")
    # Allow flag anywhere using argparse
    parser = argparse.ArgumentParser(prog="/ask_illa", add_help=False)
    parser.add_argument("-a", "--anonymous", action="store_true")
    parser.add_argument("question", nargs="*")

    try:
        args = parser.parse_args(shlex.split(text))
        question = " ".join(args.question).strip()
        if not question:
            raise ValueError("No question provided.")
    except Exception:
        await ack()
        return await respond(
            ":warning: Usage: `/ask_illa [--anonymous|-a] <your question>`\n"
            "Example: `/ask_illa -a What time is the meeting?`",
            response_type="ephemeral"
        )

    # Patch values into the body for downstream use
    body["text"] = question
    body["keep_anonymous"] = args.anonymous

    await ack()
    await respond(":hourglass: Working on it…")
    asyncio.create_task(process_and_respond(body, slack_bolt_app.client))

def _format_answer(answer: str, user_id: str, question: str, is_error: bool = False) -> str:
    """
    Format the answer to include user mention and question context.
    """
    if is_error:
        return (
            f"{user_id} asked:\n> {question}\n\n"
            f"Unfortunately, I couldn't find an answer for that. "
            "But I have posted your question in the #faq channel for others to help out!"
        )
    return (
        f"{user_id} asked:\n> {question}\n\n"
        f"Here's what I found:\n> {answer}. If this was helpful, feel free to upvote it! :thumbsup:\n\n"
    )
async def process_and_respond(body, client):
    question     = body["text"]
    user_id      = body["user_id"]
    channel_id   = body["channel_id"]
    is_anonymous = body.get("keep_anonymous", False)
    
    if is_anonymous:
        user_id = "Someone"
    else:
        user_id = f"<@{user_id}>"

    llm_answer = await get_answer(
        question=question,
        user_id=user_id,
        client=client
    )
    

    if llm_answer["status"] == "error":
        await client.chat_postMessage(
            channel=channel_id,
            text=_format_answer(llm_answer["error_message"], user_id, question, is_error=True)
        )
    else:
        await client.chat_postMessage(
            channel=channel_id,
            text=_format_answer(llm_answer["message"], user_id, question)
        )
    

@app.post("/slack/commands")
async def slack_commands(request: Request):
    return await slack_handler.handle(request)

@app.post("/slack/events")
async def slack_events(request: Request):
    return await slack_handler.handle(request)

@app.get("/slack/_ping")
async def slack_ping():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
