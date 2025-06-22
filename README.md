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

## Tech Stack
- Python 3.11+
- Slack SDK
- Google Gemini
- Google Cloud Run / Compute Engine (deployment)

### Demo GIF with a chat app integration
| Stage 1 | Stage 2 |
|:---:|:---:|
| **Ask Ella → instant reply from knowledge base**![Demo 1](https://github.com/user-attachments/assets/f3470e94-80a7-4c12-b2b4-3ff4f8c5006b) | **Agent sending unknown question  → #faq**![FAQ Crop GIF from ezgif (1)](https://github.com/user-attachments/assets/4a48e900-a6ee-4e74-9d60-fbb0a7dbdea1)
| **Stage 3: Help is saved to knowledge base**<br>![Demo 3](https://github.com/user-attachments/assets/b757d16d-54f5-4a9f-8a60-669cf6ebeb71) <br>| **Stage 4: Repeated question auto answered***<br>![Demo 4](https://github.com/user-attachments/assets/80332381-f490-482c-9ce0-cddbe0513066) |

Note: Our architecture currently supports slack for demo, and teams using different chat platforms can directly use google-adk default interface without any issues!

## Contributing
Pull requests are welcome! 🌟


© 2025 Ella | All Rights Reserved
