from __future__ import annotations

from pathlib import Path

import yaml


def load_content(path: str) -> dict:
    content_path = Path(path)
    if not content_path.is_absolute():
        cwd_candidate = Path.cwd() / content_path
        project_root = Path(__file__).resolve().parents[2]
        root_candidate = project_root / content_path
        if cwd_candidate.exists():
            content_path = cwd_candidate
        else:
            content_path = root_candidate
        if not content_path.exists():
            raise FileNotFoundError(
                "content file not found; tried "
                f"{cwd_candidate} and {root_candidate}"
            )
    with content_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)
