"""retire_runtime_helpers

Revision ID: 0002_retire_runtime_helpers
Revises: 0001_baseline
Create Date: 2026-04-20 01:52:57.053780

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_retire_runtime_helpers"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "framework_analysis_results" in inspector.get_table_names():
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_framework_analysis_results_payload_hash
            ON framework_analysis_results (payload_hash)
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "framework_analysis_results" in inspector.get_table_names():
        op.execute("DROP INDEX IF EXISTS ix_framework_analysis_results_payload_hash")
