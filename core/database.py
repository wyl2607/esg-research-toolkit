from pathlib import Path
from collections.abc import Generator
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL, make_url
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
_logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _assert_migration_gate() -> None:
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


def _run_alembic_upgrade_head() -> None:
    from alembic import command
    from alembic.config import Config

    repo_root = Path(__file__).resolve().parent.parent
    alembic_ini = repo_root / "alembic.ini"
    if not alembic_ini.exists():
        raise RuntimeError(
            f"Alembic init requested but config file is missing: {alembic_ini}"
        )
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(repo_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
    command.upgrade(alembic_cfg, "head")


def _is_in_memory_sqlite_url(database_url: str) -> bool:
    try:
        parsed: URL = make_url(database_url)
    except Exception:  # noqa: BLE001
        return database_url in {"sqlite://", "sqlite:///:memory:"}
    if parsed.get_backend_name() != "sqlite":
        return False
    if parsed.database in (None, "", ":memory:"):
        return True
    if parsed.database.startswith("file:") and "memory" in parsed.database:
        return True
    return parsed.query.get("mode") == "memory"


def _legacy_runtime_init() -> None:
    # Import model modules before create_all so metadata is populated even
    # when init_db is called outside the FastAPI bootstrap path.
    from report_parser import storage as report_storage
    from esg_frameworks import storage as framework_storage
    import benchmark.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Legacy additive helpers remain for backward compatibility until full cutover.
    report_storage.ensure_storage_schema(engine)
    framework_storage.ensure_framework_storage_schema(engine)


def init_db() -> None:
    if settings.use_alembic_init:
        if _is_in_memory_sqlite_url(settings.database_url):
            _logger.warning(
                "USE_ALEMBIC_INIT=true with in-memory sqlite URL (%s); "
                "falling back to legacy create_all path.",
                settings.database_url,
            )
            _legacy_runtime_init()
        else:
            _run_alembic_upgrade_head()
    else:
        if settings.enforce_migration_gate and settings.app_env == "production":
            _assert_migration_gate()
        _legacy_runtime_init()

    if settings.enforce_migration_gate and settings.app_env == "production":
        _assert_migration_gate()
