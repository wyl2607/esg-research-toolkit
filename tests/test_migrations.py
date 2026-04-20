from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil

import pytest
from sqlalchemy import create_engine, inspect, text

pytest.importorskip("alembic", reason="Alembic is required for migration smoke tests")
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from core.config import settings
from core.database import Base
import core.database as database_runtime
import benchmark.models  # noqa: F401
import esg_frameworks.storage  # noqa: F401
import report_parser.storage  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "alembic"
FIXTURE_DB = Path(__file__).resolve().parent / "fixtures" / "legacy_esg.db"


@contextmanager
def _temporary_database_url(database_url: str):
    previous = settings.database_url
    settings.database_url = database_url
    try:
        yield
    finally:
        settings.database_url = previous


def _alembic_config() -> Config:
    if not ALEMBIC_INI.exists() or not ALEMBIC_SCRIPT_LOCATION.exists():
        pytest.skip("Alembic config not found yet; migration tests are scaffolding-only for now")

    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    return cfg


def _revision_state(cfg: Config) -> tuple[list[str], list[str]]:
    script = ScriptDirectory.from_config(cfg)
    revisions = list(script.walk_revisions())
    if not revisions:
        pytest.skip("No Alembic revisions in alembic/versions yet")

    heads = script.get_heads()
    if not heads:
        pytest.skip("Alembic revisions exist but no head revision is discoverable")

    root_revisions = [rev.revision for rev in revisions if rev.down_revision is None]
    return heads, root_revisions


def _upgrade_head(cfg: Config, sqlite_db_path: Path) -> None:
    with _temporary_database_url(f"sqlite:///{sqlite_db_path}"):
        command.upgrade(cfg, "head")


def _stamp(cfg: Config, sqlite_db_path: Path, revision: str) -> None:
    with _temporary_database_url(f"sqlite:///{sqlite_db_path}"):
        command.stamp(cfg, revision)


def _read_alembic_versions(sqlite_db_path: Path) -> list[str]:
    engine = create_engine(f"sqlite:///{sqlite_db_path}")
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num")).scalars().all()
        return rows
    finally:
        engine.dispose()


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_row_counts(sqlite_db_path: Path, tables: list[str]) -> dict[str, int]:
    engine = create_engine(f"sqlite:///{sqlite_db_path}")
    try:
        with engine.connect() as conn:
            counts: dict[str, int] = {}
            for table in tables:
                counts[table] = int(
                    conn.execute(text(f"SELECT COUNT(*) FROM {_quote_identifier(table)}")).scalar_one()
                )
            return counts
    finally:
        engine.dispose()


def _table_shapes(sqlite_db_path: Path, tables: list[str]) -> dict[str, dict[str, set[str]]]:
    engine = create_engine(f"sqlite:///{sqlite_db_path}")
    try:
        inspector = inspect(engine)
        shapes: dict[str, dict[str, set[str]]] = {}
        for table in tables:
            shapes[table] = {
                "columns": {col["name"] for col in inspector.get_columns(table)},
                "indexes": {idx["name"] for idx in inspector.get_indexes(table)},
            }
        return shapes
    finally:
        engine.dispose()


def test_fresh_sqlite_upgrade_to_head_creates_expected_tables(tmp_path: Path) -> None:
    cfg = _alembic_config()
    expected_heads, _ = _revision_state(cfg)

    db_path = tmp_path / "fresh.sqlite3"
    _upgrade_head(cfg, db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        inspector = inspect(engine)
        actual_tables = set(inspector.get_table_names())
    finally:
        engine.dispose()

    expected_tables = set(Base.metadata.tables)
    missing_tables = expected_tables - actual_tables

    assert "alembic_version" in actual_tables
    assert not missing_tables, f"Missing tables after upgrade head: {sorted(missing_tables)}"
    assert _read_alembic_versions(db_path) == sorted(expected_heads)


def test_upgrade_head_is_idempotent_on_second_run(tmp_path: Path) -> None:
    cfg = _alembic_config()
    expected_heads, _ = _revision_state(cfg)

    db_path = tmp_path / "idempotent.sqlite3"
    _upgrade_head(cfg, db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        first_tables = sorted(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    first_versions = _read_alembic_versions(db_path)

    _upgrade_head(cfg, db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        second_tables = sorted(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    second_versions = _read_alembic_versions(db_path)

    assert first_tables == second_tables
    assert first_versions == second_versions == sorted(expected_heads)


def test_stamp_then_upgrade_preserves_existing_fixture_data(tmp_path: Path) -> None:
    if not FIXTURE_DB.exists():
        pytest.skip(f"Legacy fixture DB missing: {FIXTURE_DB}")

    cfg = _alembic_config()
    expected_heads, root_revisions = _revision_state(cfg)

    if len(root_revisions) != 1:
        pytest.skip(
            f"Expected exactly one Alembic root revision for stamp test, got {len(root_revisions)}"
        )

    db_path = tmp_path / "legacy.sqlite3"
    shutil.copy2(FIXTURE_DB, db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        inspector = inspect(engine)
        pre_tables = sorted(
            table
            for table in inspector.get_table_names()
            if table != "alembic_version" and not table.startswith("sqlite_")
        )
    finally:
        engine.dispose()

    pre_counts = _table_row_counts(db_path, pre_tables)
    if pre_tables and not any(count > 0 for count in pre_counts.values()):
        pytest.skip("Fixture DB has no rows to validate data preservation")

    _stamp(cfg, db_path, root_revisions[0])
    _upgrade_head(cfg, db_path)
    reference_db_path = tmp_path / "reference-upgrade.sqlite3"
    _upgrade_head(cfg, reference_db_path)

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        post_tables = set(inspect(engine).get_table_names())
        with engine.connect() as conn:
            integrity = conn.execute(text("PRAGMA integrity_check")).scalar_one()
    finally:
        engine.dispose()

    post_counts = _table_row_counts(db_path, pre_tables)
    managed_tables = sorted(Base.metadata.tables)
    schema_after_stamp = _table_shapes(db_path, managed_tables)
    schema_from_fresh_upgrade = _table_shapes(reference_db_path, managed_tables)

    missing_after_upgrade = [table for table in pre_tables if table not in post_tables]
    assert not missing_after_upgrade, f"Tables disappeared after stamp+upgrade: {missing_after_upgrade}"
    assert integrity == "ok"
    assert _read_alembic_versions(db_path) == sorted(expected_heads)
    for table in managed_tables:
        assert schema_from_fresh_upgrade[table]["columns"].issubset(
            schema_after_stamp[table]["columns"]
        )
        assert schema_from_fresh_upgrade[table]["indexes"].issubset(
            schema_after_stamp[table]["indexes"]
        )

    for table in pre_tables:
        assert post_counts[table] >= pre_counts[table], (
            f"Row count unexpectedly dropped for {table}: "
            f"before={pre_counts[table]}, after={post_counts[table]}"
        )


def test_init_db_with_alembic_flag_falls_back_for_in_memory_sqlite(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    runtime_engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    monkeypatch.setattr(database_runtime, "engine", runtime_engine)
    monkeypatch.setattr(settings, "database_url", "sqlite://")
    monkeypatch.setattr(settings, "use_alembic_init", True)
    monkeypatch.setattr(settings, "enforce_migration_gate", False)
    monkeypatch.setattr(settings, "app_env", "development")

    with caplog.at_level("WARNING", logger="core.database"):
        database_runtime.init_db()

    tables = set(inspect(runtime_engine).get_table_names())
    runtime_engine.dispose()
    assert "company_reports" in tables
    assert "alembic_version" not in tables
    assert "falling back to legacy create_all path" in caplog.text
