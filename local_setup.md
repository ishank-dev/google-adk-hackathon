## Quick Start

```bash
# Clone the repo
git clone https://github.com/ishank-dev/google-adk-hackathon
cd google-adk-hackathon

# Install dependencies
pip install -r requirements.txt

# Fire it up
python main.py
```

You would also need to plug in envrionment variables for the following:

```bash
GOOGLE_GENAI_USE_VERTEXAI=0
GOOGLE_API_KEY=
PROJECT_ID=
LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=
GOOGLE_STORAGE_BUCKET=
# Slack Variables
SLACK_APP_TOKEN='xapp-*' # Just let it be dummy if not using Slack

SLACK_BOT_TOKEN='xoxb-*' # Just let it be dummy if not using Slack
SLACK_SIGNING_SECRET=
```

Access the hosted URL

## Tech Stack
- Python 3.13+
- Slack SDK
- Google Gemini
- Google Cloud Run / Compute Engine (deployment)
