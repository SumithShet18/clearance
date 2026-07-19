from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]
_DB = _ROOT / "data" / "clearance.db"
_UPLOADS = _ROOT / "data" / "uploads"


def _env_password() -> str:
    """Read password from env with common aliases (Render / Docker / local)."""
    for key in (
        "CLEARANCE_PASSWORD",
        "clearance_password",
        "CLEARANCE_PASS",
        "APP_PASSWORD",
    ):
        val = os.environ.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


class Settings(BaseSettings):
    # Prefer real process env over any .env file (Render injects env at runtime)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        # env wins over env_file
        env_ignore_empty=True,
    )

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    clearance_mode: str = "mock"  # mock | llm
    clearance_erp: str = "mock"  # mock | mcp
    clearance_demo: bool = True
    # Explicit env name so Render CLEARANCE_PASSWORD always maps
    clearance_password: str = Field(default="", validation_alias="CLEARANCE_PASSWORD")
    session_secret: str = Field(
        default="clearance-dev-secret-change-me",
        validation_alias="SESSION_SECRET",
    )
    database_url: str = f"sqlite+aiosqlite:///{_DB.as_posix()}"
    upload_dir: str = str(_UPLOADS)
    confidence_hitl_threshold: float = 0.85
    rate_limit_per_minute: int = 60
    demo_api_key: str = ""
    require_demo_key: bool = False
    high_value_threshold: float = 10_000.0
    unknown_vendor_threshold: float = 500.0

    @field_validator("clearance_password", mode="before")
    @classmethod
    def _strip_password(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("clearance_demo", mode="before")
    @classmethod
    def _parse_bool(cls, v: object) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or v == "":
            return True
        return str(v).strip().lower() in {"1", "true", "yes", "on"}

    def model_post_init(self, __context: object) -> None:
        # Belt-and-suspenders: if Field default won but OS has the secret, use OS
        if not self.clearance_password:
            from_os = _env_password()
            if from_os:
                object.__setattr__(self, "clearance_password", from_os)

    @property
    def use_llm(self) -> bool:
        return bool(self.openai_api_key) and self.clearance_mode.lower() == "llm"

    @property
    def erp_backend(self) -> str:
        return "mcp" if self.clearance_erp.lower() == "mcp" else "mock"

    @property
    def auth_required(self) -> bool:
        # Always re-check OS env so mid-process / mis-load cases still work
        if self.clearance_password.strip():
            return True
        return bool(_env_password())

    @property
    def effective_password(self) -> str:
        return self.clearance_password.strip() or _env_password()


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
