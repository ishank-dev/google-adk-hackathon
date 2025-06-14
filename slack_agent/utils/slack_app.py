from slack_bolt.async_app import AsyncApp
from slack_agent.utils.config import env_config
from google.adk.sessions import InMemorySessionService
from slack_sdk.errors import SlackApiError


app = AsyncApp(
    token=env_config.slack_bot_token,
    signing_secret=env_config.slack_signing_secret,
)
session_service = InMemorySessionService()
user_to_session_mapping = {}  # slack_user_id -> adk_session_id
async def get_or_create_session(user_id: str) -> str:
    """Get existing session or create new one for the user."""
    if user_id in user_to_session_mapping:
        return user_to_session_mapping[user_id]
    
    try:
        session = await session_service.create_session(
            app_name="slack_agent",
            user_id=user_id,
        )
        user_to_session_mapping[user_id] = session.id
        print(f"Created new session {session.id} for user {user_id}")
        return session.id
    except Exception as e:
        print(f"Error creating session for user {user_id}: {e}")
        raise

async def delete_messages(channel_id: str, user_id: str, bot_user_id: str) -> str:
    """Delete bot messages in the DM channel."""
    try:
        # Fetch message history
        result = await app.client.conversations_history(channel=channel_id, limit=100)
        messages = result.get("messages", [])
        
        bot_deleted = 0
        
        for msg in messages:
            ts = msg.get("ts")
            msg_user_id = msg.get("user")
            msg_bot_id = msg.get("bot_id")
            
            try:
                # Delete bot messages
                if msg_bot_id or msg_user_id == bot_user_id:
                    await app.client.chat_delete(channel=channel_id, ts=ts)
                    bot_deleted += 1
            except SlackApiError as e:
                print(f"Error deleting message {ts}: {e.response['error']}")
                continue
        
        return f"Deleted {bot_deleted} bot messages"
    
    except SlackApiError as e:
        print(f"Error fetching history: {e.response['error']}")
        return f"Error clearing messages: {e.response['error']}"
