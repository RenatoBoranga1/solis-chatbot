from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Solar Soluções Solis"
    app_env: str = "development"
    app_debug: bool = True
    api_base_url: str = "http://localhost:8000"
    frontend_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    database_url: str = "postgresql+psycopg://solis:solis_dev_password@localhost:5432/solis"
    redis_url: str | None = None

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    field_encryption_key: str = "change-this-32-byte-minimum-secret"

    openai_api_key: str | None = None
    ai_provider: str = "openai"
    ai_model: str = "gpt-4.1-mini"
    enable_generative_ai: bool = False

    whatsapp_provider: str | None = None
    whatsapp_webhook_secret: str | None = None
    whatsapp_api_token: str | None = None
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_business_account_id: str | None = None
    whatsapp_verify_token: str = "solis_verify_token_dev"
    whatsapp_app_secret: str | None = None
    whatsapp_api_version: str = "v20.0"

    attachment_storage: str = "local"
    attachment_base_url: AnyHttpUrl | str = "http://localhost:8000/uploads"
    proposal_storage_path: str = "storage/proposals"

    rate_limit_per_minute: int = 80
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
