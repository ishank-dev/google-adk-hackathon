import os
import re
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from datetime import datetime
import time
# Load .env variables
load_dotenv()

# Initialize Slack Bolt app
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)
handler = SlackRequestHandler(app)

# Optional: confirm token loading
print("BOT TOKEN:", os.environ.get("SLACK_BOT_TOKEN"))
print("SIGNING SECRET:", os.environ.get("SLACK_SIGNING_SECRET"))

# Initialize Flask app
flask_app = Flask(__name__)

# Slack verification challenge handler
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.get_json()
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    return handler.handle(request)

@app.event("app_mention")
def mention_handler(event, say, client):
    print("📥 Bot received an app_mention event")  # Confirm handler is triggered

    try:
        channel_id = event["channel"]
        thread_ts = event.get("thread_ts", event["ts"])
        text = event.get("text", "")
        user = event["user"]

        print(f"🔎 Received text: {text}")

        # Extract number from text like "@faqsave 3"
        match = re.search(r'\b(\d+)\b', text)
        count = int(match.group(1)) if match else 5
        print(f"📊 Will save last {count} messages")

        time.sleep(1)  # ⏱️ wait 1 second before calling Slack API

        # Fetch last N messages
        history = client.conversations_history(
            channel=channel_id,
            latest=str(time.time()),
            limit=count+1,
            inclusive=False
        )
        messages = history.get("messages", [])[1:]  # Exclude the mention
        # messages = history.get("messages", [])
        messages = messages[:count]

        # # Create save directory and filename
        # timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # save_dir = "saved_logs"
        # os.makedirs(save_dir, exist_ok=True)
        # filename = os.path.join(save_dir, f"saved_messages_{count}_{timestamp}.txt")

        # # Write messages to file
        # with open(filename, "w") as f:
        #     for msg in reversed(messages):
        #         text_content = msg.get("text", "").strip()
        #         if text_content:
        #             f.write(text_content + "\n")

        # print(f"✅ Messages saved to: {filename}")
        # say(f"✅ Saved the last {count} messages to `{filename}`", thread_ts=thread_ts)

        # 🧠 Get username from Slack
        user_info = client.users_info(user=user)
        username = user_info["user"]["name"]  # e.g., "shivani"

        # 🕒 Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # 📁 Prepare save path
        save_dir = "saved_logs"
        os.makedirs(save_dir, exist_ok=True)

        # 📝 Compose filename
        filename = os.path.join(save_dir, f"{username}_faq_{count}_{timestamp}.md")

        # 🖊️ Write content to .md file
        with open(filename, "w") as f:
            f.write(f"# Saved Slack FAQ by {username} at {timestamp}\n\n")
            for i, msg in enumerate(reversed(messages), start=1):
                text_content = msg.get("text", "").strip()
                if text_content:
                    f.write(text_content + "\n")

        print(f"✅ Messages saved to: {filename}")
        say(f"✅ Saved the last {count} messages to `{filename}`", thread_ts=thread_ts)


    except Exception as e:
        import traceback
        traceback.print_exc()  # Print full error to terminal
        say(f"⚠️ Error saving messages: {str(e)}", thread_ts=thread_ts)


# Run the Flask server
if __name__ == "__main__":
    flask_app.run(port=3000)
