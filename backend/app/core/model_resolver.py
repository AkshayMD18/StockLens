from app.core.config import GROQ_PROVIDER, OLLAMA_PROVIDER
from app.core.groq import create_groq_model
from app.core.ollama import create_ollama_model
from app.db.database import SessionLocal
from app.db.model_repository import get_active_model


def active_chat_model():
    db = SessionLocal()
    try:
        record = get_active_model(db)
    finally:
        db.close()

    if record is None:
        raise RuntimeError("No active model is configured. Run database migrations first.")
    if record.provider == OLLAMA_PROVIDER:
        return create_ollama_model(record.name)
    if record.provider == GROQ_PROVIDER:
        return create_groq_model(record.name)
    raise RuntimeError(f"Unsupported model provider: {record.provider}")
