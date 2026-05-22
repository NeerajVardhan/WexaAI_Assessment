from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "WexaAI Analytics"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://wexa:wexa@localhost:5432/wexa"
    secret_key: str = Field(default="replace-with-a-long-random-secret", min_length=16)
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    backend_cors_origins: list[str | AnyHttpUrl] = ["http://localhost:3000"]
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    redis_url: str = "redis://localhost:6379/2"
    smtp_from: str = "reports@wexa.local"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = False
    webhook_timeout_seconds: int = 8
    public_base_url: str = "http://localhost:8001"
    report_artifacts_dir: str = "report_artifacts"
    enable_graphql: bool = True
    enable_otel: bool = False

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

