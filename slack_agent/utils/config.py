from dotenv import load_dotenv
import os
load_dotenv()
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

class Config:
    
    def __init__(self):
        
        # Google configuration
        self.google_genai_use_vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
        self.google_api_key = os.environ['GOOGLE_API_KEY']
        
        # Slack configuration
        self.slack_app_id = os.environ.get('SLACK_APP_ID','')
        self.slack_client_id = os.environ.get('SLACK_CLIENT_ID', '')
        self.slack_client_secret = os.environ.get('SLACK_CLIENT_SECRET','')
        self.slack_signing_secret = os.environ['SLACK_SIGNING_SECRET']
        self.slack_verification_token = os.environ.get('SLACK_VERIFICATION_TOKEN','')
        self.slack_auth_scope_token = os.environ.get('SLACK_AUTH_SCOPE_TOKEN','')
        self.slack_user_auth_token = os.environ.get('SLACK_USER_OAUTH_TOKEN','')
        self.slack_bot_user_oauth_token = os.environ['SLACK_BOT_USER_OAUTH_TOKEN']
        
        # Hugging Face configuration
        self.hf_token = os.environ['HF_TOKEN']
        
        # LLM configuration
        self.llm_model = os.getenv("LLM_MODEL", "llama3.2")
        
env_config = Config()