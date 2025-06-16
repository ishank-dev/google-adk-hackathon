from google.adk.agents import Agent
from qna_utils import extract_qna_from_md
import os, glob
from datetime import datetime

def build_faq_kb() -> dict:
    try:
        kb_folder = "/Users/shivanikotian/Documents/Google ADK Hackathon/Slack-FAQ-save-bot/kb_faq"
        os.makedirs(kb_folder, exist_ok=True)

        saved_files = glob.glob("/Users/shivanikotian/Documents/Google ADK Hackathon/Slack-FAQ-save-bot/saved_logs/*.md")
        faq_entries = []

        for file in saved_files:
            qna = extract_qna_from_md(file)
            base_name = os.path.basename(file).replace(".md", "")
            new_path = os.path.join(kb_folder, f"{base_name}_QnA.md")

            with open(new_path, "w") as f:
                f.write(qna.strip())

            # Log metadata if needed
            faq_entries.append({
                "source_file": file,
                "generated_file": new_path,
                "summary": qna.strip()
            })

        return {"status": "success", "entries": faq_entries}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "error_message": str(e)}

root_agent = Agent(
    name="faq_extractor_agent",
    model="gemini-1.5-flash",
    description="Extracts FAQ from Slack logs and updates the central FAQ KB",
    instruction=(
        "On activation, run `build_faq_kb()` to extract question-answer pairs "
        "from Markdown logs and save them to the central knowledge base."
    ),
    tools=[build_faq_kb],
)

if __name__ == "__main__":
    result = build_faq_kb()
    print(result)
