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

## Bonus Points Blog & Podcast
- #### Medium Blog: https://medium.com/@shivanikotian18/5a41cabbef40
- #### ▶️ Listen to podcast [![Play on SoundCloud](https://img.shields.io/badge/Listen-SoundCloud-orange?logo=soundcloud)](https://on.soundcloud.com/ZKu8XMZeD41IdOX8jL)

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
## Running Locally
- [Link to Guide](https://github.com/ishank-dev/google-adk-hackathon/blob/main/local_setup.md)

## Contributing
Pull requests are welcome! 🌟
© 2025 Ella | All Rights Reserved
