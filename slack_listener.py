from slack_agent.agent import app
import os

if __name__ == "__main__":
    # Start the Slack app
    app.start(port=int(os.environ.get("PORT", 3000)))