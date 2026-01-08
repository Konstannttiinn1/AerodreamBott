from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


def now_iso(timezone: str) -> str:
    return datetime.now(ZoneInfo(timezone)).isoformat()


def now_dt(timezone: str) -> datetime:
    return datetime.now(ZoneInfo(timezone))
