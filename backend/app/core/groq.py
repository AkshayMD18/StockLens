# app/core/groq.py
from langchain_groq import ChatGroq

from app.core.config import settings


def create_groq_model(model: str):
    if settings.groq_api_key is None:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return ChatGroq(
        api_key=settings.groq_api_key.get_secret_value(),
        model=model,
        max_retries=0,
    )
