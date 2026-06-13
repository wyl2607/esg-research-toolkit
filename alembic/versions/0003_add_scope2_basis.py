"""add_scope2_basis

Adds company_reports.scope2_basis ('market' | 'location') and backfills existing
rows per the 2026-06-12 ruling: Scope 2 canonical = market-based, location only as
fallback (see docs/audits/incorrect-triage-2026-06-12.md).

Preconditions / semantics:
- Assumes the #61 precision corrections are already in place (local + VPS synced,
  confirmed PLANS.md 2026-06-12). Running this before #61 could pair a basis label
  with a stale value.
- downgrade is lossy for basis labels: a re-upgrade only restores the *initial*
  adjudication (22 market + RWE AG 2023 location). Any location label added after
  this migration cannot be reconstructed by the backfill.

Revision ID: 0003_add_scope2_basis
Revises: 0002_retire_runtime_helpers
Create Date: 2026-06-13

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_add_scope2_basis"
down_revision: str | None = "0002_retire_runtime_helpers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "company_reports",
        sa.Column("scope2_basis", sa.String(), nullable=True),
    )

    bind = op.get_bind()
    # Idempotent (WHERE scope2_basis IS NULL): non-null Scope 2 → 'market'.
    bind.execute(
        sa.text(
            """
            UPDATE company_reports
            SET scope2_basis = 'market'
            WHERE scope2_co2e_tonnes IS NOT NULL AND scope2_basis IS NULL
            """
        )
    )
    # RWE AG 2023 is the sole location-fallback row. Match by name+year (local and
    # prod ids differ — never anchor on id).
    result = bind.execute(
        sa.text(
            """
            UPDATE company_reports
            SET scope2_basis = 'location'
            WHERE company_name = 'RWE AG' AND report_year = 2023
              AND scope2_co2e_tonnes IS NOT NULL
            """
        )
    )
    # SEC-3 guard: if an RWE 2023 row with a Scope 2 value exists but the exact-name
    # UPDATE matched nothing, a name variant silently kept 'market' — fail loudly.
    # Fresh/empty DBs (no such row) pass through untouched.
    rwe_present = bind.execute(
        sa.text(
            """
            SELECT COUNT(*) FROM company_reports
            WHERE company_name LIKE '%RWE%' AND report_year = 2023
              AND scope2_co2e_tonnes IS NOT NULL
            """
        )
    ).scalar_one()
    if rwe_present and result.rowcount == 0:
        raise RuntimeError(
            "scope2_basis backfill: RWE 2023 Scope 2 row present but exact-name "
            "UPDATE matched 0 rows — company_name variant would mislabel it 'market'. "
            "Reconcile the name before upgrading."
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("company_reports") as batch_op:
        batch_op.drop_column("scope2_basis")
