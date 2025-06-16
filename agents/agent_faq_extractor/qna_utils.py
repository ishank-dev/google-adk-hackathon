from vertexai import init
from vertexai.generative_models import GenerativeModel
import os
import google.auth
from dotenv import load_dotenv
load_dotenv() 

# ✅ Function to extract Q&A from markdown Slack logs
def extract_qna_from_md(md_path):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    prompt = f"""
You are a helpful assistant. The following is a Slack conversation:

\"\"\"\n{content}\n\"\"\"

Based on the messages, extract:
1. One meaningful question someone is likely asking.
2. The most appropriate answer from the discussion.

Return ONLY in this format:

Q: <question>
A: <answer>
    """

    # ✅ Load creds + project settings from environment
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION")

    if not all([GOOGLE_APPLICATION_CREDENTIALS, PROJECT_ID, LOCATION]):
        raise ValueError("Missing required environment variables.")

    # ✅ Use the service account credentials
    creds, _ = google.auth.load_credentials_from_file(GOOGLE_APPLICATION_CREDENTIALS)

    # ✅ Initialize Vertex AI with credentials
    init(project=PROJECT_ID, location=LOCATION, credentials=creds)

    # ✅ Use Gemini model
    model = GenerativeModel("gemini-2.0-flash-001")
    response = model.generate_content(prompt)

    return response.text

