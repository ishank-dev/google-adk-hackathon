# Ella (Effortless Learning & Lookup Assistant)

Ella is an AI agent that helps you automatically transforms your team’s resolved chat threads into a living FAQ document so no question has to be answered twice.

## 60-Second Pitch

- ⚡ **Instant answers**: Ella searches its Knowledge Base built on historical conversations and replies in real time.
- 🙋 **Escalates smartly**: No answer? Ella posts the question to **#faq** channel so teammates can jump in.
- 🧠 **Self-learning**: Once solved, Ella stores the new Q&A, eliminating repeat questions.

## Full Deck Link:

- https://google-adk-hackathon-demo.my.canva.site/

## Watch the Demo Pitch here:

- https://www.youtube.com/watch?v=dxeVhAzYlFI

## Alternatively Try the Live Demo:

- http://34.172.141.166:8000/dev-ui/

## How It Works

1. **Ask** → User messages Ella.
2. **Search** → Ella scans the Knowledge Base.
3. **Answer / Escalate** → Replies instantly or posts to **#faq**.
4. **Learn** → Saves the new answer for next time.

## Architecture

High Level Workflow
![Screen Recording Jun 20 2025 Crop (1)](https://github.com/user-attachments/assets/b1249aa4-bdaa-4c1e-95cf-2a95d905f8eb)

Agent Level Workflow
![Screen Recording Jun 20 2025 Crop](https://github.com/user-attachments/assets/ec15a845-1600-467a-9552-f169577cad70)

- **Read Agent** forwards the question to Vertex AI (Gemini + RAG).
- Vertex AI pulls relevant documents from a Cloud Storage corpus, combines them with the LLM, and returns an answer.
- FastAPI delivers Ella’s reply back.
- If the user (or teammate) runs `/add_doc`, the **Write & Curate Agent** stores the new document in Cloud Storage, expanding the corpus that RAG searches next time.

### Demo GIF with a chat app integration

|                                                                     Stage 1                                                                     |                                                                         Stage 2                                                                          |
| :---------------------------------------------------------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------: |
|   **Ask Ella → instant reply from knowledge base**![Screen Recording 2025-06-22 at 7 13 58 PM](https://github.com/user-attachments/assets/f8e601e6-bf40-45f5-a074-93a6f679afc3)   | **Agent sending unknown question → #faq**![FAQ Crop GIF from ezgif (1)](https://github.com/user-attachments/assets/4a48e900-a6ee-4e74-9d60-fbb0a7dbdea1) |
| **Stage 3: Help is saved to knowledge base**<br>![Demo 3](https://github.com/user-attachments/assets/b757d16d-54f5-4a9f-8a60-669cf6ebeb71) <br> |        **Stage 4: Repeated question auto answered**<br>![Demo 4](https://github.com/user-attachments/assets/80332381-f490-482c-9ce0-cddbe0513066)        |

Note: Our architecture currently supports slack for demo, and teams using different chat platforms can directly use google-adk default interface without any issues!


## Quick Start

You would need to plug in envrionment variables for the following:

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

# HuggingFace
HF_TOKEN='hf_*'

# LLM Model
LLM_MODEL='llama3.1:8b' # Just let it be dummy if not using local LLM
```

```bash
# Clone the repo
git clone https://github.com/ishank-dev/google-adk-hackathon
cd google-adk-hackathon

# Install dependencies
pip install -r requirements.txt

# Fire it up
python main.py
```

If you're using poetry or uv for package management, you can run the following commands:

```bash
# Install dependencies using poetry
poetry install --no-root
```

## Tech Stack

- Python 3.11+
- Slack SDK
- Google Gemini
- Google Cloud Run / Compute Engine (deployment)

# ADK Agents Reference

> **Scope** – This document explains the two production‑grade agents that ship with our Agent Development Kit (ADK): **Document Agent** and **QnA Agent**. It also documents the supporting config, Slack glue‑code, and extension points so you can adapt or extend the system quickly.

---

## 1. Architecture at a Glance

| Component      | Purpose                                                                       | Runtime Model      | Entrypoint                       | Key Tool(s)                 |
| -------------- | ----------------------------------------------------------------------------- | ------------------ | -------------------------------- | --------------------------- |
| Document Agent | Ingests user‑supplied text into the RAG corpus after relevance + dedup checks | `gemini-2.0-flash` | `agents/document_agent/agent.py` | `post_document_to_corpus()` |
| QnA Agent      | Answers questions strictly from the Markdown knowledge‑base (RAG)             | `gemini-2.0-flash` | `agents/qna_agent/agent.py`      | `chat_kb()`                 |
| Config Loader  | Centralises ENV vars for GCP, Slack, HF, Ollama                               | `utils/config.py`  | n/a                              | n/a                         |
| Slack Bridge   | Creates ADK sessions per Slack user & routes messages                         | `slack_app.py`     | n/a                              | `delete_messages()`         |

---

## 2. Document Agent

### 2.1 Responsibilities

1. Accept raw text from Slack (or any caller)
2. Decide **relevance** (LLM‑prompt + keyword fallback)
3. Prevent duplicates (exact hash + optional semantic similarity)
4. Chunk & import the doc into Vertex AI RAG corpus
5. Return a structured JSON result (`success`, `skipped`, `rejected`, or `error`)

### 2.2 Public Tool

```python
async def post_document_to_corpus(text_content: str) -> dict
```

- `-f` / `--force` flag bypasses relevance check
- Returns the merged result of `add_to_document()` and lower‑level helpers

### 2.3 Workflow

```
┌──── user text ────┐
│ 1. Agent picks up │
└────────┬──────────┘
         │
         ▼
check_content_relevance →   reject : accept ↴
                                   │
                                   ▼
             add_document_to_vectorstore (hash‑dedup → semantic‑dedup → GCS upload → rag.import_files)
                                   │
                                   ▼
                            JSON result to caller
```

### 2.4 Key Flags & Thresholds

| Setting                | Default | Description                                      |
| ---------------------- | ------- | ------------------------------------------------ |
| `RELEVANCE_THRESHOLD`  | `60`    | min score (0‑100) from LLM JSON to accept        |
| `similarity_threshold` | `0.85`  | cosine similarity to treat as semantic duplicate |
| `chunk_size`           | `1000`  | bytes per RAG chunk                              |
| `chunk_overlap`        | `200`   | byte overlap between chunks                      |

### 2.5 Example Slack Usage

```
/doc "Team‑wide VPN Configuration Guide – 2025" -f
```

---

## 3. QnA Agent

### 3.1 Responsibilities

- Retrieve relevant contexts from the Vertex AI RAG corpus
- Assemble a system‑prompt with numbered **Sources** + user **Question**
- Generate a grounded answer; refuse or fallback if corpus lacks coverage

### 3.2 Public Tool

```python
def chat_kb(question: str) -> dict
```

- Always returns `{status: 'success'|'error', …}`
- Root agent instruction forces _every_ user message through this tool

### 3.3 Safety & Answering Rules

- Hard‑wired safety blocklist (weapons, self‑harm, illegal detail)
- If no context → fallback LLM or polite uncertainty message
- Encourages users to add missing docs via **Document Agent**

### 3.4 Example Interaction

```
User → “How do I rotate GKE credentials?”
Agent → calls chat_kb → returns grounded answer with inline source refs.
```

---

## 4. Configuration & Environment Variables

All secrets / IDs live in **`.env`** and are loaded via `utils.config.Config`.

| Var                                        | Purpose                                         |
| ------------------------------------------ | ----------------------------------------------- |
| `GOOGLE_API_KEY`                           | Public or service‑account key for Gemini API    |
| `GOOGLE_PROJECT_ID` / `GOOGLE_LOCATION`    | GCP project & region                            |
| `GOOGLE_STORAGE_BUCKET`                    | GCS bucket that stores corpus files             |
| `SLACK_BOT_TOKEN` / `SLACK_SIGNING_SECRET` | Slack app credentials                           |
| `HF_TOKEN`                                 | Hugging Face access (optional)                  |
| `LLM_MODEL`                                | Ollama local model for dev (`llama3.2` default) |

_(See `utils/config.py` for the full list)_

---

## 5. Slack Integration Flow

1. **AsyncApp** receives a DM or slash‑command
2. `get_or_create_session` maps Slack user → ADK session (in‑memory)
3. Message text is forwarded to **QnA Agent**; if doc ingest, to **Document Agent**
4. Helper `delete_messages()` can wipe bot history on demand

> **Note** – replace `InMemorySessionService` with Redis or Firestore for multi‑instance deployments.

---

## 6. Extending the System

| Task                               | Where to patch                                                   | Notes                              |
| ---------------------------------- | ---------------------------------------------------------------- | ---------------------------------- |
| Add a new ingest format (e.g. CSV) | `add_document_to_vectorstore` – preprocess & set `doc_type`      | Provide your own chunker or parser |
| Custom relevance rules             | `check_content_relevance`                                        | Tweak prompt or threshold          |
| Swap LLM model                     | Update `root_agent.model` + ensure model is enabled in Vertex AI | Keep prompt length limits in mind  |
| Persist sessions                   | Replace `InMemorySessionService`                                 | E.g. Firestore, Redis, SQL         |

---

## 7. Error Codes & Debugging Tips

| Status                           | Typical Cause                    | Fix                                                |
| -------------------------------- | -------------------------------- | -------------------------------------------------- |
| `rejected`                       | Relevance score < 60             | Add `-f` flag or improve doc quality               |
| `skipped` + `exact_duplicate`    | Hash match                       | No action – already stored                         |
| `skipped` + `semantic_duplicate` | Similarity ≥ 0.85                | Consider force‑adding if intentionally overlapping |
| `error`                          | GCP creds, GCS ACL, Vertex quota | Check ENV vars & IAM roles                         |

Enable `logging.DEBUG` to see raw API payloads and similarity scores.

---

## 8. Security & Governance

- All uploads stored under `gs://{GOOGLE_STORAGE_BUCKET}/{corpus}/documents/`
- File metadata records uploader (`user_id`) and timestamp for audit
- Safety prompts enforced at answer‑time; dangerous requests are refused

---

## 9. Versioning & Roll‑Back

- Corpus files are immutable; updates create new timestamped objects
- Hash‑based deduplication prevents accidental overwrite
- To purge everything, call `clear_knowledge_base()` (admin‑only)

---

## 10. Quick Start

```bash
# 1. Set environment variables (.env)
# 2. Run the Slack bot
python main.py
# 3. Ask a question:
"How do we trigger failover in prod?"
```

That’s it – you now have ingestion + retrieval backed by Vertex AI RAG, wrapped in two simple agents ready for production or extension.

## Contributing

Pull requests are welcome! 🌟

© 2025 Ella | All Rights Reserved
