from functools import lru_cache
import json

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Solar Soluções Solis"
    app_env: str = "development"
    app_debug: bool = True
    api_base_url: str = "http://localhost:8000"
    frontend_origins_raw: str = Field(
        default="http://localhost:5173",
        validation_alias="FRONTEND_ORIGINS",
    )

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
    chat_attachment_storage_path: str = "storage/chat_attachments"
    proposal_storage_path: str = "storage/proposals"
    proposal_public_base_url: AnyHttpUrl | str | None = None

    energy_bill_extraction_enabled: bool = True
    energy_bill_ocr_enabled: bool = False
    energy_bill_ocr_provider: str = "disabled"
    energy_bill_ocr_max_pages: int = 3
    energy_bill_min_text_length: int = 80
    energy_bill_allow_external_ai: bool = False
    energy_bill_max_file_size_mb: int = 10
    energy_bill_store_raw_text: bool = False
    energy_bill_min_confidence_auto_apply: float = 0.85
    energy_bill_storage_path: str = "storage/energy_bills"

    company_name: str = "Solar Solucoes"
    company_phone: str | None = None
    company_email: str | None = None
    company_website: AnyHttpUrl | str = "https://solarsolucoes.com.br"
    company_address: str | None = None
    company_logo_path: str | None = None
    company_primary_color: str = "#FFCC33"
    company_secondary_color: str = "#0B1F33"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Solar Solucoes"
    smtp_use_tls: bool = True

    rate_limit_per_minute: int = 80
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def frontend_origins(self) -> list[str]:
        value = self.frontend_origins_raw.strip()
        if not value:
            return ["http://localhost:5173"]
        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
