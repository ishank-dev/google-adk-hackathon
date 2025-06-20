import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
import asyncio

from modules.qna_utils import add_to_document

async def post_document_to_corpus(text_content: str) -> dict:
    """Tool to post a document to the corpus."""
    lower_text = text_content.lower()
    force_add = "-f" in lower_text or "--force" in lower_text
    if force_add:
        text_content = text_content.replace("-f", "").replace("--force", "").strip()
    result = await add_to_document(text_content, force_add=force_add)
    
    return result

root_agent = Agent(
    name="document_agent",
    model="gemini-2.0-flash",
    instruction="Use post_document_to_corpus to add documents to the corpus.",
    description="Post documents to the corpus and answer user queries.",
    tools=[post_document_to_corpus],
)

