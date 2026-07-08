from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from core.database import _ensure_sqlite_parent_dir


def test_creates_missing_nested_parent_dirs(tmp_path: Path) -> None:
    db_file = tmp_path / "does" / "not" / "exist" / "esg_toolkit.db"
    database_url = f"sqlite:///{db_file.as_posix()}"
    assert not db_file.parent.exists()

    _ensure_sqlite_parent_dir(database_url)

    assert db_file.parent.is_dir()
    # The engine must now be able to open the database file.
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar() == 1
    finally:
        engine.dispose()
    assert db_file.exists()


def test_existing_parent_dir_is_untouched(tmp_path: Path) -> None:
    db_file = tmp_path / "esg_toolkit.db"
    _ensure_sqlite_parent_dir(f"sqlite:///{db_file.as_posix()}")
    assert tmp_path.is_dir()


def test_in_memory_and_non_sqlite_urls_are_noops() -> None:
    # Must not raise or attempt any filesystem work.
    _ensure_sqlite_parent_dir("sqlite://")
    _ensure_sqlite_parent_dir("sqlite:///:memory:")
    _ensure_sqlite_parent_dir("postgresql+psycopg://user:pass@localhost/esg")
    _ensure_sqlite_parent_dir("not a url")
