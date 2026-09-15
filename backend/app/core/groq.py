# app/core/groq.py
from langchain_groq import ChatGroq

from app.core.config import settings

if settings.groq_api_key is None:
    raise RuntimeError("GROQ_API_KEY is not configured")

groq_model = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model,
    max_retries=0,
)
