from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1"
    openai_validation_model: str = "gpt-4o-mini"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "sqlite:///./data/esg_toolkit.db"
    arxiv_max_results: int = 20
    arxiv_download_pdf: bool = True
    log_level: str = "INFO"
    batch_max_workers: int = 2

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
