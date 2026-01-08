from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _parse_admin_ids(raw: str) -> set[int]:
    return {int(item.strip()) for item in raw.split(",") if item.strip()}


def _load_dotenv() -> None:
    """Load .env from project root if it exists (local/dev friendly)."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(slots=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    admin_tg_url: str
    site_url: str
    map_url: str
    broadcast_rate_limit: int
    database_path: str
    timezone: str
    enable_automation: bool

    @classmethod
    def from_env(cls) -> "Config":
        _load_dotenv()
        bot_token = os.environ.get("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required")
        admin_ids = _parse_admin_ids(os.environ.get("ADMIN_IDS", ""))
        admin_tg_url = os.environ.get("ADMIN_TG_URL", "").strip()
        site_url = os.environ.get("SITE_URL", "").strip()
        map_url = os.environ.get("MAP_URL", "").strip()
        broadcast_rate_limit = int(os.environ.get("BROADCAST_RATE_LIMIT", "200"))
        database_path = os.environ.get("DATABASE_PATH", "data/bot.db")
        timezone = os.environ.get("TIMEZONE", "Europe/Moscow")
        enable_automation = os.environ.get("ENABLE_AUTOMATION", "false").lower() in {"1", "true", "yes"}
        db_path = Path(database_path).expanduser().resolve()
        return cls(
            bot_token=bot_token,
            admin_ids=admin_ids,
            admin_tg_url=admin_tg_url,
            site_url=site_url,
            map_url=map_url,
            broadcast_rate_limit=broadcast_rate_limit,
            database_path=str(db_path),
            timezone=timezone,
            enable_automation=enable_automation,
        )
