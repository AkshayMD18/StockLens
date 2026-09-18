"""add prompt to strategies

Revision ID: 76f531975c49
Revises: bef31d86ce14
Create Date: 2026-09-18 13:23:58.175754
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "76f531975c49"
down_revision: Union[str, None] = "bef31d86ce14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "strategies",
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("strategies", "prompt", server_default=None)


def downgrade() -> None:
    op.drop_column("strategies", "prompt")
