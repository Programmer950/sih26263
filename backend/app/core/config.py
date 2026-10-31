"""Application Settings & Environment Configuration."""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import os


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:root@127.0.0.1:5432/apaar_setu",
        description="PostgreSQL Database Connection URL",
    )

    # Cryptographic Secrets
    JWT_SECRET_KEY: str = Field(
        ...,
        description="256-bit secret key for signing JWT tokens",
    )
    DATA_ENCRYPTION_KEY: str = Field(
        ...,
        description="256-bit secret key for AES-256-GCM data encryption at rest",
    )
    BLIND_INDEX_SECRET_KEY: str = Field(
        ...,
        description="Dedicated 256-bit secret key for deterministic HMAC blind index lookups",
    )

    # Token Expiration
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Storage & File Ingestion Configuration (Milestone 3)
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    STORAGE_ENCRYPTION_KEY: str = Field(
        default="3034bb1956a6c08e3836cecfcbc86992aaa389267a29cf28e4ccc9415174b1f6",
        description="256-bit secret key for AES-256-GCM file storage encryption at rest",
    )
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_UNCOMPRESSED_ARCHIVE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MAX_ARCHIVE_ENTRY_COUNT: int = 500
    MAX_COMPRESSION_RATIO: int = 20
    MAX_ROW_COUNT: int = 25000
    MAX_COL_COUNT: int = 50
    PARSER_TIMEOUT_SECONDS: int = 30
    RETENTION_DAYS_COMMITTED: int = 1825  # Policy-driven default: 5 years
    RETENTION_DAYS_CANCELLED: int = 90    # Policy-driven default: 90 days

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        return v

    @field_validator("JWT_SECRET_KEY", "DATA_ENCRYPTION_KEY", "BLIND_INDEX_SECRET_KEY")
    @classmethod
    def validate_key_strength(cls, v: str, info) -> str:
        if not v or len(v.strip()) < 32:
            raise ValueError(f"{info.field_name} must be at least 32 characters (256-bit entropy).")
        return v

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

