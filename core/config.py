from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1"  # legacy alias for extraction model
    openai_extraction_model: str = ""
    openai_validation_model: str = "gpt-5.4-mini"
    openai_audit_model: str = "gpt-4o"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:4173"
    admin_api_token: str = ""
    database_url: str = "sqlite:///./data/esg_toolkit.db"
    arxiv_max_results: int = 20
    arxiv_download_pdf: bool = True
    log_level: str = "INFO"
    batch_max_workers: int = 2
    use_alembic_init: bool = False
    enforce_migration_gate: bool = True
    l0_fail_closed: bool = True
    l0_fail_open_bypass: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
