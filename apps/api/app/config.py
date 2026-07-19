from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[3]
_DB = _ROOT / "data" / "clearance.db"
_UPLOADS = _ROOT / "data" / "uploads"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    clearance_mode: str = "mock"  # mock | llm
    # ERP backend: in-process mock | MCP stdio server
    clearance_erp: str = "mock"  # mock | mcp
    # Product: show demo seed/bench UI and endpoints
    clearance_demo: bool = True
    # Single-tenant password; empty = open access (dev/demo)
    clearance_password: str = ""
    # Session secret for signed cookies
    session_secret: str = "clearance-dev-secret-change-me"
    database_url: str = f"sqlite+aiosqlite:///{_DB.as_posix()}"
    upload_dir: str = str(_UPLOADS)
    confidence_hitl_threshold: float = 0.85
    rate_limit_per_minute: int = 60
    demo_api_key: str = ""
    require_demo_key: bool = False
    # Policy defaults (overridden by SettingsRow in DB when present)
    high_value_threshold: float = 10_000.0
    unknown_vendor_threshold: float = 500.0

    @property
    def use_llm(self) -> bool:
        return bool(self.openai_api_key) and self.clearance_mode.lower() == "llm"

    @property
    def erp_backend(self) -> str:
        return "mcp" if self.clearance_erp.lower() == "mcp" else "mock"

    @property
    def auth_required(self) -> bool:
        return bool(self.clearance_password.strip())


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
