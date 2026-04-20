from pathlib import Path

import pytest
from sqlalchemy import create_engine

from alembic import command
from alembic.config import Config

from core.limiter import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter() -> None:
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture(scope="session")
def migrated_engine(tmp_path_factory: pytest.TempPathFactory):
    """Session-scoped SQLite engine initialized via Alembic head."""
    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic.ini"
    alembic_dir = repo_root / "alembic"
    if not alembic_ini.exists() or not alembic_dir.exists():
        pytest.skip("Alembic config is missing; cannot create migrated_engine fixture")

    db_path = tmp_path_factory.mktemp("db") / "migrated_template.sqlite3"
    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(alembic_dir))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    try:
        yield engine
    finally:
        engine.dispose()
