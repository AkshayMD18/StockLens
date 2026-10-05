from langchain_ollama import ChatOllama

from app.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL


ollama_model = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
