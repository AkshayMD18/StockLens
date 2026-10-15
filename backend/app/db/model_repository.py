from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.llm_models import LLMModel


def get_active_model(db: Session) -> LLMModel | None:
    return db.scalar(select(LLMModel).where(LLMModel.status == "active"))


def get_models(db: Session) -> list[LLMModel]:
    return list(db.scalars(select(LLMModel).order_by(LLMModel.id)))


def switch_model(db: Session, qualified_name: str) -> LLMModel:
    provider, separator, name = qualified_name.partition("/")
    if not separator:
        raise ValueError(f"Unknown model: {qualified_name}")

    selected = db.scalar(
        select(LLMModel).where(LLMModel.provider == provider, LLMModel.name == name)
    )
    if selected is None:
        raise ValueError(f"Unknown model: {qualified_name}")

    db.execute(update(LLMModel).values(status="inactive"))
    selected.status = "active"
    db.commit()
    db.refresh(selected)
    return selected
