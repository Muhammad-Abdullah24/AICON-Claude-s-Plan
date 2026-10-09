"""Backend settings, read once from the environment (and .env at the repo root)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(REPO_ROOT / ".env")

# How many weeks of history the forecast endpoint returns, ending at as_of.
HISTORY_WEEKS = 104


@dataclass(frozen=True)
class Settings:
    cors_origins: list[str]


def get_settings() -> Settings:
    origins = os.environ.get("FS_CORS_ORIGINS", "http://localhost:5173")
    return Settings(
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
    )
