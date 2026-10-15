"""create llm models table

Revision ID: c01d8f0f5401
Revises: 76f531975c49
Create Date: 2026-10-15 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c01d8f0f5401"
down_revision: Union[str, None] = "76f531975c49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm_models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_llm_models_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "name", name="uq_llm_models_provider_name"),
    )
    op.create_index(
        "uq_llm_models_active_status",
        "llm_models",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.bulk_insert(
        sa.table(
            "llm_models",
            sa.column("provider", sa.String),
            sa.column("name", sa.String),
            sa.column("status", sa.String),
        ),
        [
            {"provider": "ollama", "name": "qwen3:8b", "status": "active"},
            {"provider": "groq", "name": "openai/gpt-oss-20b", "status": "inactive"},
            {"provider": "groq", "name": "openai/gpt-oss-120b", "status": "inactive"},
        ],
    )


def downgrade() -> None:
    op.drop_table("llm_models")
