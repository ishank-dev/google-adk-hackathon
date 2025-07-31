"""
agent.py – ADK entry-point for OpenAI agent. Imports rag_kb_openai.chat and exposes it as a tool.
"""
from google.adk.agents import Agent
from . import rag_kb_openai          # leading dot = same package


def chat_kb(question: str) -> dict:
    try:
        answer = rag_kb_openai.chat(question)     # history defaults to []
        return {"status": "success", "answer": answer}
    except Exception as exc:
        import traceback, sys
        traceback.print_exc(file=sys.stdout)   # so you see future errors
        return {"status": "error", "error_message": str(exc)}


root_agent = Agent(
    name="openai_rag_agent",
    model="gemini-2.0-flash",  # Use ADK-supported model for agent framework
    description="Answers strictly from the Markdown knowledge base using OpenAI GPT-4o backend.",
    instruction=(
        "For **every** user message (question, statement, anything):\n"
        "  1. Call chat_kb(question=<entire user message>).  \n"
        "  2. If status=='success', reply ONLY with the 'answer' text.\n"
        "  3. If status=='error', apologise and show the error message.\n"
        "Do not reply in any other format."
    ),
    tools=[chat_kb],
)
