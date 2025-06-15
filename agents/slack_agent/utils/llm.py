from langchain_ollama import OllamaLLM 
from agents.slack_agent.utils.config import env_config
llm = OllamaLLM(model=env_config.llm_model)
