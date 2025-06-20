from langchain_ollama import OllamaLLM 
from agents.messaging_agent.utils.config import env_config
llm = OllamaLLM(model=env_config.llm_model)
