from __future__ import annotations

import yaml


def load_content(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)
