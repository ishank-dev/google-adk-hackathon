from agents.slack_agent.utils.config import env_config
from agents.multi_tool_agent_gemini.rag_kb_gemini import GeminiFAQSystem
import json
import os
if __name__ == "__main__":
    # Configuration - Update these with your actual values
    PROJECT_ID = env_config.google_project_id
    LOCATION = env_config.google_location
    SERVICE_ACCOUNT_PATH = env_config.google_credentials_path  # Replace with your path
    KNOWLEDGE_BASE_PATH = "knowledge_base"  # Path to your documents
    
    # Initialize the FAQ system
    try:
        faq_system = GeminiFAQSystem(
            project_id=PROJECT_ID,
            location=LOCATION,
            service_account_path=SERVICE_ACCOUNT_PATH,
            corpus_name="FAQ-Knowledge-Base"
        )
        
        print("🎉 FAQ System initialized successfully!")
        print("\n📚 Updating knowledge base...")
        if os.path.exists(KNOWLEDGE_BASE_PATH):
            stats = faq_system.update(KNOWLEDGE_BASE_PATH)
            print(f"Upload stats: {stats}")
        else:
            print(f"⚠️ Knowledge base path not found: {KNOWLEDGE_BASE_PATH}")
        
        # Example 2: Get corpus information
        print("\nℹ️ Corpus information:")
        info = faq_system.get_corpus_info()
        print(json.dumps(info, indent=2, default=str))
        
        # Example 3: Answer a question
        print("\n❓ Answering question...")
        question = "How do we make data pipelines here?"
        answer = faq_system.answer(question)
        print(f"Q: {question}")
        print(f"A: {answer}")
        
        # Example 4: Chat interface
        print("\n💬 Chat interface example...")
        conversation = []
        
        questions = [
            "How do I know which codebase is safe to modify?"
        ]
        
        for q in questions:
            try:
                answer, conversation = faq_system.chat(q, conversation)
                print(f"Q: {q}")
                print(f"A: {answer}\n")
            except Exception as e:
                print(f"Error answering '{q}': {str(e)}")
        
        # # Example 5: Direct LLM access
        # print("🤖 Direct LLM access example...")
        # llm_response = faq_system.llm("Explain the benefits of using RAG for FAQ systems in 3 bullet points")
        # print(f"LLM Response: {llm_response}")
        
    except Exception as e:
        print(f"❌ Failed to initialize FAQ system: {str(e)}")
        print("Please check your configuration and ensure all required services are enabled.")