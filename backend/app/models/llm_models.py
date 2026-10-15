from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class LLMModel(Base):
    __tablename__ = "llm_models"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'inactive')", name="ck_llm_models_status"),
        UniqueConstraint("provider", "name", name="uq_llm_models_provider_name"),
        Index(
            "uq_llm_models_active_status",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
