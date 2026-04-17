from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import settings

# ── Engine config (SQLite local / Postgres VPS) ─────────────────────────
# Switching to Postgres on the VPS only requires `DATABASE_URL=postgresql+psycopg://...`
# in the env. SQLAlchemy ignores pool_size/pool_pre_ping for SQLite, so the
# same code works in both modes.
_is_sqlite = settings.database_url.startswith("sqlite")

_connect_args: dict = {}
_engine_kwargs: dict = {"pool_pre_ping": True}

if _is_sqlite:
    _connect_args["check_same_thread"] = False
else:
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 1800,
        }
    )

engine = create_engine(settings.database_url, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    if settings.enforce_migration_gate and settings.app_env == "production":
        inspector = inspect(engine)
        if "alembic_version" not in inspector.get_table_names():
            raise RuntimeError(
                "Migration gate failed: missing alembic_version table in production. "
                "Run DB migrations before starting the service."
            )
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar()
        if not version:
            raise RuntimeError(
                "Migration gate failed: alembic_version has no version_num. "
                "Run DB migrations before starting the service."
            )

    Base.metadata.create_all(bind=engine)
    # Keep SQLite deployments forward-compatible for additive columns.
    from report_parser.storage import ensure_storage_schema
    from esg_frameworks.storage import ensure_framework_storage_schema

    ensure_storage_schema(engine)
    ensure_framework_storage_schema(engine)
