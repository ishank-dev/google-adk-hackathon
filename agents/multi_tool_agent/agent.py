"""
agent.py – ADK entry-point.  Imports rag_kb.chat and exposes it as a tool.
"""
from google.adk.agents import Agent
from . import rag_kb       # leading dot = same package


def chat_kb(question: str) -> dict:
    try:
        answer = rag_kb.chat(question)     # history defaults to []
        return {"status": "success", "answer": answer}
    except Exception as exc:
        import traceback, sys
        traceback.print_exc(file=sys.stdout)   # so you see future errors
        return {"status": "error", "error_message": str(exc)}


root_agent = Agent(
    name="md_rag_agent",
    model="gemini-2.0-flash",
    description="Answers strictly from the Markdown knowledge base.",
    instruction=(
        "For **every** user message (question, statement, anything):\n"
        "  1. Call chat_kb(question=<entire user message>).  \n"
        "  2. If status=='success', reply ONLY with the 'answer' text.\n"
        "  3. If status=='error', apologise and show the error message.\n"
        "Do not reply in any other format."
    ),
    tools=[chat_kb],
    # max_iterations=1  ← delete this line
)


