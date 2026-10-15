from langchain_ollama import ChatOllama

from app.core.config import OLLAMA_BASE_URL


def create_ollama_model(model: str):
    return ChatOllama(model=model, base_url=OLLAMA_BASE_URL)
