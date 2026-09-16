from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Strategy


def get_all_strategies(db: Session) -> list[Strategy]:
    return list(db.scalars(select(Strategy).order_by(Strategy.id)))
