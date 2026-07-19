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
    # ERP backend: in-process mock | MCP stdio server (mcp-servers/erp/server.py)
    clearance_erp: str = "mock"  # mock | mcp
    database_url: str = f"sqlite+aiosqlite:///{_DB.as_posix()}"
    upload_dir: str = str(_UPLOADS)
    confidence_hitl_threshold: float = 0.85
    # Public demo hardening: mutating requests per IP per window (0 = off)
    rate_limit_per_minute: int = 30
    # Optional shared secret: X-Clearance-Key bypasses rate limit; if require_demo_key, required for writes
    demo_api_key: str = ""
    require_demo_key: bool = False

    @property
    def use_llm(self) -> bool:
        return bool(self.openai_api_key) and self.clearance_mode.lower() == "llm"

    @property
    def erp_backend(self) -> str:
        return "mcp" if self.clearance_erp.lower() == "mcp" else "mock"


settings = Settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
