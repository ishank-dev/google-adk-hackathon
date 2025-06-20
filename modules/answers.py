from typing import Dict, Optional
from agents.multi_tool_agent_gemini.rag_kb_gemini import faq_system


unanswered_questions = [
    "I don't have information about this in my knowledge base.",
    "I don't have enough information to answer this question.",
    "I couldn't find relevant information in our knowledge base to answer your question"
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
        enable_fallback = True
        if "--strict" in question:
            enable_fallback = False
            question = question.replace("--strict", "").strip()
        (answer,_) = faq_system.chat(question, enable_fallback = enable_fallback)
        unanswered_question = any(q in answer for q in unanswered_questions)
        if unanswered_question:
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