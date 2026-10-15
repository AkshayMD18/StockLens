from rich.table import Table

from app.db.database import SessionLocal
from app.db.model_repository import get_models, switch_model


async def list_models() -> Table:
    db = SessionLocal()
    try:
        models = get_models(db)
    finally:
        db.close()

    table = Table(title="LLM Models")
    table.add_column("Model")
    table.add_column("Status")
    for model in models:
        table.add_row(f"{model.provider}/{model.name}", model.status)
    return table


async def select_model(qualified_name: str) -> str:
    db = SessionLocal()
    try:
        selected = switch_model(db, qualified_name)
        return f"Active model: {selected.provider}/{selected.name}"
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
