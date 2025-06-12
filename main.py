# main.py
import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import uvicorn
from fastapi import Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from ticketing_agent.agent import app as slack_bolt_app
from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agents_dir="agents",    # where your `root_agent` modules live
    web=True,               # serve the UI at "/"
)

slack_handler = AsyncSlackRequestHandler(slack_bolt_app)

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
