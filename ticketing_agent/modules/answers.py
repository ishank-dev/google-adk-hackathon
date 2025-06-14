from typing import Dict, Optional
from slack_agent.utils.llm import llm
# from multi_tool_agent_llama.rag_kb_llm import chat
from multi_tool_agent_llama.rag_kb_llm import chat
import re
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
            f":triangular_flag_on_post: {user_id} asked:\n> {question}\n\n"
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
        print(f"Error processing question: {e}")
        return {"status": "error", "error_message": "Internal error, please try again later."}