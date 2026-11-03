from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        extra="ignore",
    )

    database_url: str = ""
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)
    max_upload_rows: int = Field(default=5000, ge=1, le=5000)
    virustotal_api_key: str = ""
    google_webrisk_api_key: str = ""
    rdap_enabled: bool = False
    provider_timeout_seconds: float = Field(default=4.0, gt=0, le=15)
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
