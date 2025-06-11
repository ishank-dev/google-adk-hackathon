from slack_agent.utils.slack_app import app
from slack_agent.utils.llm import llm
from slack_sdk.errors import SlackApiError

@app.command("/help_illa_public")
async def public_query_handler(ack, respond, command):
    # 1. ACK immediately so Slack knows we're alive
    await ack()

    channel = command["channel_id"]
    # slash commands normally don't post your text, but if it did, you'd have a ts
    orig_ts = command.get("message_ts") or command.get("ts")

    # helper to delete the original if possible
    async def try_delete():
        if orig_ts:
            try:
                await app.client.chat_delete(channel=channel, ts=orig_ts)
            except SlackApiError:
                pass

    # 2. “Working on it” ack in thread
    thread_ts = orig_ts
    await respond(
        text="Let me work through it and get back to you…",
        thread_ts=thread_ts,
        response_type="ephemeral",
    )

    user_text = command.get("text", "").strip()

    # 3. PII detection
    pi_prompt = (
        "Detect whether the following text contains personal or sensitive information "
        "(emails, phone numbers, addresses, SSNs, etc.).\n\n"
        f"Text: \"{user_text}\"\n\n"
        "Answer with exactly 'yes' or 'no'."
    )
    pi_response = llm(pi_prompt)
    if "yes" in pi_response.lower():
        # delete the original invocation if it showed up
        await try_delete()
        return await respond(
            text="⚠️ I spotted personal info in your request. Please remove it and try again.",
            thread_ts=thread_ts,
            response_type="ephemeral"
        )

    # 4. Intent classification
    intent_prompt = (
        "Classify the following user question into one of: public, private, inappropriate. "
        "Respond with exactly one of these words.\n\n"
        f"Question: \"{user_text}\""
    )
    intent = llm(intent_prompt).strip().lower()

    if intent == "private":
        # delete original, then invite to DM
        await try_delete()
        await app.client.chat_postMessage(
            channel=command["user_id"],
            text="🔒 That seems like a private question. Let's chat here in DM."
        )

    elif intent == "inappropriate":
        # delete original, then warn ephemerally
        await try_delete()
        await respond(
            text="🚫 That question seems inappropriate. Please refrain from asking it.",
            thread_ts=thread_ts,
            response_type="ephemeral"
        )

    else:
        # TODO: Replace with Ishank's Model
        answer = llm(f"Provide a concise, helpful answer to: {user_text}")
        await respond(text=answer, thread_ts=thread_ts)
