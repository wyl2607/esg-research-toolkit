"""One-time migration: fix FrameworkAnalysisResult rows with framework_version='v1'."""

from __future__ import annotations

import os
import sys

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.database import engine
from esg_frameworks.schemas import FRAMEWORK_VERSIONS


def run(bind_engine: Engine | None = None) -> int:
    fixed = 0
    target_engine = bind_engine or engine
    inspector = inspect(target_engine)
    table_name = "framework_analysis_results"
    if not inspector.has_table(table_name):
        print(f"Backfill skipped: '{table_name}' table not found")
        return fixed

    available_columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }
    required_columns = {"framework_id", "framework_version"}
    if not required_columns.issubset(available_columns):
        print(
            "Backfill skipped: missing required columns "
            f"{sorted(required_columns - available_columns)}"
        )
        return fixed

    with target_engine.begin() as conn:
        for framework_id, canonical_version in FRAMEWORK_VERSIONS.items():
            result = conn.execute(
                text(
                    "UPDATE framework_analysis_results "
                    "SET framework_version = :ver "
                    "WHERE framework_id = :fid "
                    "AND framework_version = 'v1' "
                    "AND framework_version != :ver"
                ),
                {"ver": canonical_version, "fid": framework_id},
            )
            fixed += result.rowcount
    print(f"Backfill complete: {fixed} rows updated")
    return fixed


if __name__ == "__main__":
    run()
