# main.py
import os
from typing import Dict
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import uvicorn
import asyncio, shlex, argparse
from fastapi import Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from utils.slack_app import app as slack_bolt_app
from google.adk.cli.fast_api import get_fast_api_app
from modules.answers import get_answer
from modules.qna_utils import add_to_document, get_document_stats

app = get_fast_api_app(
    agents_dir="agents",    # where your `root_agent` modules live
    web=True,               # serve the UI at "/"
)

slack_handler = AsyncSlackRequestHandler(slack_bolt_app)


@slack_bolt_app.command("/ask_ella")
async def handle_ask_ella(ack, body, respond):
    text = body.get("text", "")

    try:
        tokens = text.split()
        parser = argparse.ArgumentParser(prog="/ask_ella", add_help=False)
        parser.add_argument("-a", "--anonymous", action="store_true")
        args, remainder = parser.parse_known_args(tokens)
        question = " ".join(remainder).strip()
        if not question:
            raise ValueError("No question provided.")
    except Exception:
        await ack()
        return await respond(
            ":warning: Usage: `/ask_ella [--anonymous|-a] <your question>`\n"
            "Example: `/ask_ella -a What time is the meeting?`",
            response_type="ephemeral"
        )

    # Patch values into the body for downstream use
    body["text"] = question
    body["keep_anonymous"] = args.anonymous

    await ack()
    await respond(":hourglass: Working on it…")
    asyncio.create_task(process_and_respond(body, slack_bolt_app.client))


@slack_bolt_app.command("/add_to_document")
async def handle_add_to_document(ack, body, respond):
    text = body.get("text", "")
    
    # Parse arguments for the add_to_document command
    parser = argparse.ArgumentParser(prog="/add_to_document", add_help=False)
    parser.add_argument("-t", "--title", help="Title for the document/section")
    parser.add_argument("-c", "--category", help="Category/doc_type for the document")
    parser.add_argument("-f", "--force", action="store_true", help="Skip relevance check")
    parser.add_argument("content", nargs="*", help="Content to add")

    try:
        args = parser.parse_args(shlex.split(text))
        content = " ".join(args.content).strip()
        if not content:
            raise ValueError("No content provided.")
    except Exception:
        await ack()
        return await respond(
            ":warning: Usage: `/add_to_document [-t title] [-c category] [-f] <content>`\n"
            "Example: `/add_to_document -t 'Meeting Notes' -c team_updates 'Weekly standup notes from 2025-06-15'`\n"
            "Use `-f` to skip relevance checking and force addition.",
            response_type="ephemeral"
        )

    await ack()
    await respond(":hourglass: Analyzing content relevance and adding to database…")
    
    # Process the document addition in background
    asyncio.create_task(process_document_addition(
        body, 
        slack_bolt_app.client, 
        content, 
        args.title, 
        args.category, 
        args.force
    ))


@slack_bolt_app.event("app_mention")
async def handle_app_mention(event, client):
    """
    Handle app mentions for adding documents from threads.
    Supports two formats:
    1. @bot add_doc [title="..."] [category="..."] [force] <optional additional context>
    2. @bot N (where N is the number of messages to save)
    """
    text = event.get("text", "").strip()
    user_id = event.get("user")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts")  # This will be present if in a thread
    message_ts = event.get("ts")
    
    # Add initial reaction to acknowledge we received the command
    await client.reactions_add(
        channel=channel_id,
        timestamp=message_ts,
        name="hourglass_flowing_sand"
    )
    if "testing_ella" in text.lower():
        await client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts or message_ts,
            text="🤖 I can hear you! App mentions are working."
        )
        return
    
    try:
        # Check if this is a number command
        if _is_number_command(text):
            count = _parse_number_command(text)
            
            # Get the last N messages
            content = await get_last_n_messages(client, channel_id, thread_ts, count)
            
            # Add to knowledge base with default values
            result = await add_to_document(
                content=content,
                title="Slack Thread",
                category="general",
                force_add=True,  # Skip relevance check for number-based saves
                user_id=user_id,
                context_info=f"Last {count} messages"
            )
            
            # Remove hourglass reaction
            try:
                await client.reactions_remove(
                    channel=channel_id,
                    timestamp=message_ts,
                    name="hourglass_flowing_sand"
                )
            except:
                pass
            
            if result["status"] == "success":
                await client.reactions_add(
                    channel=channel_id,
                    timestamp=message_ts,
                    name="white_check_mark"
                )
                
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts or message_ts,
                    text=f"✅ Saved last {count} messages to the knowledge base."
                )
            else:
                await client.reactions_add(
                    channel=channel_id,
                    timestamp=message_ts,
                    name="x"
                )
                
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts or message_ts,
                    text=f":x: Error saving messages: {result.get('error', 'Unknown error occurred')}"
                )
            return
        
        # Check if this is an add_doc command
        is_add_doc = _is_add_doc_command(text)
        
        if is_add_doc:
            # Parse the command
            parsed_command = _parse_add_doc_command(text, user_id)
            
            if parsed_command["error"]:
                # Remove hourglass and add error reaction
                await client.reactions_remove(
                    channel=channel_id,
                    timestamp=message_ts,
                    name="hourglass_flowing_sand"
                )
                await client.reactions_add(
                    channel=channel_id,
                    timestamp=message_ts,
                    name="warning"
                )
                
                await client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts or message_ts,
                    text=f":warning: {parsed_command['error']}\n\n"
                         f"**Usage:** `@bot add_doc [title=\"...\"] [category=\"...\"] [force] <optional context>`\n"
                         f"**Example:** `@bot add_doc title=\"Meeting Notes\" category=\"team_updates\" This thread discusses our new process`"
                )
                return
            
            # Process in background
            asyncio.create_task(process_mention_document_addition(
                client, channel_id, user_id, thread_ts, message_ts, parsed_command
            ))
            return
            
        # If we get here, check if it's a test message
        if "test" in text.lower():
            await client.chat_postMessage(
                channel=channel_id,
                thread_ts=thread_ts or message_ts,
                text="🤖 I can hear you! App mentions are working."
            )
            return
            
        # If we get here, it's an unknown command
        # Remove hourglass and add warning reaction
        await client.reactions_remove(
            channel=channel_id,
            timestamp=message_ts,
            name="hourglass_flowing_sand"
        )
        await client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name="warning"
        )
        
        await client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts or message_ts,
            text=":warning: Unknown command. Use `@bot N` to save last N messages or `@bot add_doc` to add specific content."
        )
        
    except Exception as e:
        # Remove hourglass and add error reaction
        try:
            await client.reactions_remove(
                channel=channel_id,
                timestamp=message_ts,
                name="hourglass_flowing_sand"
            )
        except:
            pass
        
        await client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name="x"
        )
        
        await client.chat_postMessage(
            channel=channel_id,
            thread_ts=thread_ts or message_ts,
            text=f":x: Error processing command: {str(e)}"
        )


def _is_add_doc_command(text: str) -> bool:
    """
    Check if the mention text contains an add_doc command.
    We look for specific patterns to avoid interfering with other bot usage.
    """
    # Remove bot mention and normalize
    cleaned_text = text.lower().strip()
    
    # Remove common bot mention patterns - fix the regex to handle both uppercase and lowercase
    import re
    cleaned_text = re.sub(r'<@[uw][a-z0-9]+>', '', cleaned_text, flags=re.IGNORECASE).strip()
    
    # Check for our specific command patterns - must be at the start
    patterns = [
        r'^add_doc\b',           # starts with add_doc
        r'^add-doc\b',           # starts with add-doc  
        r'^adddoc\b',            # starts with adddoc
        r'^save_thread\b',       # alternative: save_thread
        r'^save-thread\b',       # alternative: save-thread
    ]
    
    return any(re.match(pattern, cleaned_text) for pattern in patterns)


def _parse_add_doc_command(text: str, user_id: str) -> Dict:
    """
    Parse the add_doc command to extract parameters.
    Format: @bot add_doc [title="..."] [category="..."] [force] <additional context>
    """
    try:
        import re
        
        # Remove bot mention - fix case sensitivity issue
        cleaned_text = re.sub(r'<@[uw][a-z0-9]+>', '', text, flags=re.IGNORECASE).strip()
        
        # Remove the command word - find which command was used
        original_cleaned = cleaned_text
        for cmd in ['add_doc', 'add-doc', 'adddoc', 'save_thread', 'save-thread']:
            if cleaned_text.lower().startswith(cmd):
                cleaned_text = cleaned_text[len(cmd):].strip()
                break
        
        # If no command was found, return error
        if cleaned_text == original_cleaned:
            return {
                "error": "No valid add_doc command found",
                "title": None, "category": None, "force": False, 
                "additional_context": "", "user_id": user_id
            }
        
        # Parse parameters
        title = None
        category = None
        force = False
        additional_context = cleaned_text
        
        # Extract title="..." or title='...'
        title_match = re.search(r'title=(["\'])(.*?)\1', cleaned_text, re.IGNORECASE)
        if title_match:
            title = title_match.group(2)
            additional_context = additional_context.replace(title_match.group(0), '').strip()
        
        # Extract category="..." or category='...'
        category_match = re.search(r'category=(["\'])(.*?)\1', cleaned_text, re.IGNORECASE)
        if category_match:
            category = category_match.group(2)
            additional_context = additional_context.replace(category_match.group(0), '').strip()
        
        # Check for force flag
        if re.search(r'--force\b', cleaned_text, re.IGNORECASE):
            force = True
            additional_context = re.sub(r'\bforce\b', '', additional_context, flags=re.IGNORECASE).strip()
        
        # Clean up additional context
        additional_context = ' '.join(additional_context.split())  # normalize whitespace
        
        return {
            "error": None,
            "title": title,
            "category": category,
            "force": force,
            "additional_context": additional_context,
            "user_id": user_id
        }
        
    except Exception as e:
        return {
            "error": f"Failed to parse command: {str(e)}",
            "title": None,
            "category": None,
            "force": False,
            "additional_context": "",
            "user_id": user_id
        }


async def process_mention_document_addition(client, channel_id, user_id, thread_ts, message_ts, parsed_command):
    """
    Process document addition from app mention (works in threads).
    """
    user_mention = f"<@{user_id}>"
    reply_ts = thread_ts or message_ts
    
    try:
        # Get the full context - if thread_ts exists, we're in a thread
        if thread_ts:
            # We're in a thread - get the full thread context
            full_context = await get_thread_context_for_mention(
                client, channel_id, thread_ts, parsed_command["additional_context"]
            ) or {
                "content":"",
                "info":""
            }
        else:
            # This is a standalone mention - just use the additional context
            full_context = {
                "content": parsed_command["additional_context"] or "Document saved from Slack mention",
                "info": "standalone message"
            }
        
        # Add to knowledge base
        result = await add_to_document(
            content=full_context["content"],
            title=parsed_command["title"],
            category=parsed_command["category"],
            force_add=parsed_command["force"],
            user_id=user_id,
            context_info=full_context["info"]
        )
        
        # Update reactions based on result
        # Remove hourglass first
        try:
            await client.reactions_remove(
                channel=channel_id,
                timestamp=message_ts,
                name="hourglass_flowing_sand"
            )
        except:
            pass  # Reaction might not exist
        
        # Send response and add appropriate reaction
        if result["status"] == "success":
            # Add success reaction
            await client.reactions_add(
                channel=channel_id,
                timestamp=message_ts,
                name="white_check_mark"
            )
            
            context_msg = f" (captured {full_context['info']})" if full_context["info"] != "standalone message" else ""
            message = (
                f":white_check_mark: {user_mention} successfully added content to the knowledge base!{context_msg}\n\n"
                f"**Title:** {result['title']}\n"
                f"**Category:** {result['category']}\n"
                f"**Relevance Score:** {result.get('relevance_score', 'N/A')}\n"
                f"**Added {result['chunks_added']} chunks** to the vector database."
            )
        elif result["status"] == "rejected":
            # Add rejection reaction
            await client.reactions_add(
                channel=channel_id,
                timestamp=message_ts,
                name="no_entry_sign"
            )
            
            message = (
                f":no_entry_sign: {user_mention}, the content was not added to the knowledge base.\n\n"
                f"**Reason:** {result['reason']}\n"
                f"**Relevance Score:** {result.get('relevance_score', 'N/A')}\n\n"
                f"_Add `force` to your command to skip relevance checking._"
            )
        else:
            # Add error reaction
            await client.reactions_add(
                channel=channel_id,
                timestamp=message_ts,
                name="x"
            )
            
            message = (
                f":x: {user_mention}, there was an error adding the content:\n"
                f"{result.get('error', 'Unknown error occurred')}"
            )
            
    except Exception as e:
        # Remove hourglass and add error reaction
        try:
            await client.reactions_remove(
                channel=channel_id,
                timestamp=message_ts,
                name="hourglass_flowing_sand"
            )
        except:
            pass
        
        await client.reactions_add(
            channel=channel_id,
            timestamp=message_ts,
            name="x"
        )
        
        message = (
            f":x: {user_mention}, failed to process document addition:\n"
            f"Error: {str(e)}"
        )
    
    await client.chat_postMessage(
        channel=channel_id,
        thread_ts=reply_ts,
        text=message
    )


async def get_thread_context_for_mention(client, channel_id, thread_ts, additional_context):
    """
    Get full thread context when mentioned in a thread.
    """
    try:
        response = await client.conversations_replies(
            channel=channel_id,
            ts=thread_ts,
            limit=100
        )
        
        if response.get("ok") and response.get("messages"):
            messages = response["messages"]
            context_info = f"{len(messages)} messages from thread"
            
            # Format the thread conversation
            thread_content = []
            for msg in messages:
                user_id = msg.get("user", "Unknown")
                text = msg.get("text", "")
                
                # Skip bot messages and empty messages
                if not text.strip() or user_id == "bot":
                    continue
                
                # Get user info for better formatting
                try:
                    user_info = await client.users_info(user=user_id)
                    username = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("name") or f"User-{user_id}"
                except:
                    username = f"User-{user_id}"
                
                # Clean up bot mentions from the text
                import re
                cleaned_text = re.sub(r'<@[UW][A-Z0-9]+>', '', text).strip()
                
                if cleaned_text:
                    thread_content.append(f"**{username}:** {cleaned_text}")
            
            # Combine thread context with additional context
            thread_text = "\n\n".join(thread_content)
            
            if additional_context:
                full_content = f"THREAD CONVERSATION:\n{thread_text}\n\nADDITIONAL CONTEXT:\n{additional_context}"
            else:
                full_content = f"THREAD CONVERSATION:\n{thread_text}"
            
            return {
                "content": full_content,
                "info": context_info
            }
        
    except Exception as e:
        # Fallback to additional context only
        return {
            "content": additional_context or "Error retrieving thread context",
            "info": f"Error getting thread context: {str(e)}"
        }


@slack_bolt_app.command("/document_stats")
async def handle_document_stats(ack, body, respond):
    """
    Show statistics about the knowledge base (private responses only).
    """
    await ack()
    
    # First private response
    await respond(":hourglass: Gathering knowledge base statistics...", response_type="ephemeral")
    
    # Background processing with private follow-up
    asyncio.create_task(fetch_and_send_stats_private(respond))


async def fetch_and_send_stats_private(respond):
    """
    Background task that uses the original respond function (always private).
    """
    try:
        # This can take as long as needed
        stats = get_document_stats()
        
        if "error" in stats:
            message = f":warning: Error retrieving stats: {stats['error']}"
        else:
            doc_types_text = "\n".join([f"• {doc_type}: {count}" for doc_type, count in stats['document_types'].items()])
            message = (
                f":books: **Knowledge Base Statistics**\n\n"
                f"**Total Documents:** {stats['total_documents']}\n\n"
                f"**Document Types:**\n{doc_types_text}"
            )
    except Exception as e:
        message = f":x: Error retrieving document statistics: {str(e)}"
    
    # This will ALWAYS be private since it uses the original respond function
    await respond(message, response_type="ephemeral")


def _format_answer(answer: str, user_id: str, question: str, is_error: bool = False) -> str:
    """
    Format the answer to include user mention and question context.
    """
    if is_error:
        return (
            f"{user_id} asked:\n> {question}\n\n"
            f"Unfortunately, I couldn't find an answer for that. Either the question is invalid, or the answer is not in our knowledge base.\n\n"
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


async def process_document_addition(body, client, content, title, category, force_add):
    """
    Process the document addition request with relevance checking.
    """
    user_id = body["user_id"]
    channel_id = body["channel_id"]
    user_mention = f"<@{user_id}>"
    
    # Check if this is in a thread and gather thread context
    thread_ts = body.get("thread_ts")
    
    try:
        # Get the full context (thread + original content)
        full_context = await get_message_context(client, channel_id, content, thread_ts)
        
        result = await add_to_document(
            content=full_context["content"],
            title=title,
            category=category,
            force_add=force_add,
            user_id=user_id,
            context_info=full_context["info"]
        )
        
        if result["status"] == "success":
            context_msg = f" (including {full_context['info']})" if full_context["info"] else ""
            message = (
                f":white_check_mark: {user_mention} successfully added content to the knowledge base!{context_msg}\n\n"
                f"**Title:** {result['title']}\n"
                f"**Category:** {result['category']}\n"
                f"**Relevance Score:** {result.get('relevance_score', 'N/A')}\n"
                f"**Added {result['chunks_added']} chunks** to the vector database."
            )
        elif result["status"] == "rejected":
            message = (
                f":x: {user_mention}, the content was not added to the knowledge base.\n\n"
                f"**Reason:** {result['reason']}\n"
                f"**Relevance Score:** {result.get('relevance_score', 'N/A')}\n\n"
                f"_Use the `-f` flag to force addition if you believe this content is relevant._"
            )
        else:
            message = (
                f":warning: {user_mention}, there was an error adding the content:\n"
                f"{result.get('error', 'Unknown error occurred')}"
            )
            
    except Exception as e:
        message = (
            f":x: {user_mention}, failed to process document addition:\n"
            f"Error: {str(e)}"
        )
    
    await client.chat_postMessage(
        channel=channel_id,
        text=message
    )


async def get_message_context(client, channel_id, original_content, thread_ts=None):
    """
    Get the full context of a message, including thread history if applicable.
    """
    context_info = ""
    full_content = original_content
    
    try:
        if thread_ts:
            # This is in a thread - get the full conversation
            response = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=100  # Adjust as needed
            )
            
            if response.get("ok") and response.get("messages"):
                messages = response["messages"]
                context_info = f"{len(messages)} messages from thread"
                
                # Format the thread conversation
                thread_content = []
                for msg in messages:
                    user_id = msg.get("user", "Unknown")
                    text = msg.get("text", "")
                    timestamp = msg.get("ts", "")
                    
                    # Get user info for better formatting
                    try:
                        user_info = await client.users_info(user=user_id)
                        username = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("name") or user_id
                    except:
                        username = user_id
                    
                    if text.strip():  # Only include non-empty messages
                        thread_content.append(f"**{username}:** {text}")
                
                # Combine thread context with original content
                thread_text = "\n\n".join(thread_content)
                full_content = f"THREAD CONVERSATION:\n{thread_text}\n\nADDITIONAL CONTEXT:\n{original_content}"
        
        return {
            "content": full_content,
            "info": context_info
        }
        
    except Exception as e:
        # If we can't get thread context, fall back to original content
        return {
            "content": original_content,
            "info": f"Error getting thread context: {str(e)}"
        }


def _is_number_command(text: str) -> bool:
    """
    Check if the mention text contains a number command.
    Format: @bot N where N is a number
    """
    # Remove bot mention and normalize
    cleaned_text = text.lower().strip()
    
    # Remove common bot mention patterns
    import re
    cleaned_text = re.sub(r'<@[uw][a-z0-9]+>', '', cleaned_text, flags=re.IGNORECASE).strip()
    
    # Check if it's just a number
    return bool(re.match(r'^\d+$', cleaned_text))

def _parse_number_command(text: str) -> int:
    """
    Parse the number command to extract the count.
    Returns 5 as default if no valid number found.
    """
    import re
    # Remove bot mention
    cleaned_text = re.sub(r'<@[uw][a-z0-9]+>', '', text, flags=re.IGNORECASE).strip()
    
    # Extract number
    match = re.search(r'\b(\d+)\b', cleaned_text)
    return int(match.group(1)) if match else 5

async def get_last_n_messages(client, channel_id, thread_ts, count: int):
    """
    Get the last N messages from a thread or channel.
    """
    try:
        if thread_ts:
            # Get messages from thread
            response = await client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
                limit=count + 1  # +1 to exclude the mention message
            )
            messages = response.get("messages", [])[1:]  # Exclude the mention message
        else:
            # Get messages from channel
            response = await client.conversations_history(
                channel=channel_id,
                limit=count + 1  # +1 to exclude the mention message
            )
            messages = response.get("messages", [])[1:]  # Exclude the mention message
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            user_id = msg.get("user", "Unknown")
            text = msg.get("text", "").strip()
            
            if not text:
                continue
                
            # Get user info for better formatting
            try:
                user_info = await client.users_info(user=user_id)
                username = user_info.get("user", {}).get("real_name") or user_info.get("user", {}).get("name") or f"User-{user_id}"
            except:
                username = f"User-{user_id}"
            
            formatted_messages.append(f"**{username}:** {text}")
        
        return "\n\n".join(formatted_messages)
        
    except Exception as e:
        return f"Error retrieving messages: {str(e)}"


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