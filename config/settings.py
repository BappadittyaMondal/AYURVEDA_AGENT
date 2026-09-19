"""Application Settings and Environment Configuration for AYURVEDA_AGENT."""
import os
from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Central configuration parameters for AYURVEDA_AGENT."""
    app_name: str = Field(default="AYURVEDA_AGENT")
    app_version: str = Field(default="3.1.0-ENTERPRISE-CLINICAL")
    environment: str = Field(default="development")
    debug: bool = Field(default=True)

    # Security & Tokens
    secret_key: str = Field(
        default=os.getenv(
            "AYURVEDA_SECRET_KEY",
            "ayurveda-agent-zero-trust-clinical-governance-secret-key-3.1"
        )
    )
    token_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=480)  # 8 hours shift

    # Multi-Hospital Tenancy
    default_hospital_id: str = Field(default="aiia-delhi-central-001")

    # Persistence (SQLite WAL)
    database_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("DATABASE_DIR", "data"))
    )
    database_name: str = Field(default="ayurveda_edge.db")
    sqlite_busy_timeout_ms: int = Field(default=5000)
    sqlite_synchronous: str = Field(default="NORMAL")
    sqlite_journal_mode: str = Field(default="WAL")

    @property
    def database_path(self) -> Path:
        """Full resolved path to the SQLite edge database."""
        return self.database_dir / self.database_name


@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of Settings."""
    settings = Settings()
    settings.database_dir.mkdir(parents=True, exist_ok=True)
    return settings
