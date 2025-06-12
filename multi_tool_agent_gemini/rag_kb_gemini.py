#!/usr/bin/env python3

import os
from dotenv import load_dotenv, find_dotenv
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import AuthorizedSession

import vertexai
from vertexai.rag import (
    RagEmbeddingModelConfig,
    VertexPredictionEndpoint,
    RagVectorDbConfig,
)
from google import genai
from google.genai.types import HttpOptions
from vertexai import rag

# 1) Load environment variables
load_dotenv(find_dotenv())
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION   = os.getenv("LOCATION")
SA_KEY_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
assert PROJECT_ID and LOCATION, "Missing PROJECT_ID or LOCATION in .env"
assert SA_KEY_PATH and os.path.isfile(SA_KEY_PATH), (
    "Missing or invalid GOOGLE_APPLICATION_CREDENTIALS in .env; "
    "please set this to your service-account JSON path"
)
print(f"PROJECT_ID = {PROJECT_ID}")
print(f"LOCATION   = {LOCATION}")
print(f"Using service account credentials from {SA_KEY_PATH}")

# 2) Load service account credentials
# Load service account credentials with proper OAuth scopes
from google.oauth2.service_account import Credentials as ServiceAccountCredentialsWithScopes
creds = ServiceAccountCredentialsWithScopes.from_service_account_file(
    SA_KEY_PATH,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# 3) Initialize Vertex AI with credentials
vertexai.init(project=PROJECT_ID, location=LOCATION, credentials=creds)

# 4) Initialize GenAI (Gemini) client for Vertex AI with credentials
client = genai.Client(
    vertexai=True,
    credentials=creds,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=HttpOptions(api_version="v1"),
)
print("✅ Vertex AI and Gemini clients initialized with service account credentials")

# 5) Get or create RAG corpus for Markdown docs
DISPLAY_NAME = "MarkdownCorpus"
existing = [c for c in rag.list_corpora() if c.display_name == DISPLAY_NAME]
if existing:
    corpus = existing[0]
    print(f"📂 Using existing corpus: {corpus.name}")
else:
    EMBEDDING_MODEL_ID = "text-embedding-005"
    embedding_model_config = RagEmbeddingModelConfig(
        vertex_prediction_endpoint=VertexPredictionEndpoint(
            publisher_model=f"publishers/google/models/{EMBEDDING_MODEL_ID}"
        )
    )
    corpus = rag.create_corpus(
        display_name=DISPLAY_NAME,
        backend_config=RagVectorDbConfig(
            rag_embedding_model_config=embedding_model_config
        ),
    )
    print(f"✅ Created corpus: {corpus.name}")

# 6) Upload new .md files under knowledge-base-slack only
DOC_FOLDER  = "knowledge-base-slack"
CORPUS_NAME = corpus.name
existing_files = rag.list_files(corpus_name=CORPUS_NAME)
uploaded_names = {f.display_name for f in existing_files}

all_md = []
for root, _, files in os.walk(DOC_FOLDER):
    for fname in files:
        if fname.lower().endswith(".md"):
            path = os.path.join(root, fname)
            rel  = os.path.relpath(path, DOC_FOLDER)
            all_md.append((path, rel))

if not all_md:
    print(f"⚠️ No markdown files found in {DOC_FOLDER}")
else:
    count = 0
    for path, rel in all_md:
        if rel in uploaded_names:
            print(f"⏭️ Skipping already-uploaded: {rel}")
            continue
        print(f"Uploading: {rel}")
        rag.upload_file(
            corpus_name=CORPUS_NAME,
            path=path,
            display_name=rel,
            description="Markdown doc"
        )
        count += 1
    print(f"✅ Uploaded {count} new markdown files")

# 7) Prepare Retrieval REST endpoint & session
parent            = f"projects/{PROJECT_ID}/locations/{LOCATION}"
RETRIEVE_ENDPOINT = f"https://{LOCATION}-aiplatform.googleapis.com/v1/{parent}:retrieveContexts"
authed_session    = AuthorizedSession(creds)

# 8) Chat function: retrieve + generate

def chat(question: str) -> str:
    """
    Retrieve context from the RAG corpus and generate an answer with Gemini.
    """
    # a) Retrieve contexts
    body = {
        "vertexRagStore": {"ragResources": [{"ragCorpus": CORPUS_NAME}]},
        "query": {"text": question},
    }
    resp = authed_session.post(RETRIEVE_ENDPOINT, json=body)
    resp.raise_for_status()
    data = resp.json()
    # b) Collect snippets
    contexts = [ctx.get("text") or ctx.get("content") or "" 
                for ctx in data.get("contexts", {}).get("contexts", [])]
    # c) Build prompt
    prompt = (
        "You are a helpful assistant. Use the sources below to answer the question, "
        "and cite each fact with its source number (e.g. [1], [2]).\n\n"
    )
    for i, txt in enumerate(contexts, start=1):
        prompt += f"Source {i}: {txt}\n\n"
    prompt += f"Question: {question}\nAnswer:"
    # d) Generate answer
    response = client.models.generate_content(
        model="gemini-2.0-flash-001",
        contents=prompt,
    )
    return response.text

# If run as script, test chat
if __name__ == "__main__":
    print(chat("How do we make data pipelines here?"))
