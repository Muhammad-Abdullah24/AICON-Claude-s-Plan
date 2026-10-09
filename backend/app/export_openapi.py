"""Writes the API's OpenAPI schema for the front end to generate types from.

    python -m backend.app.export_openapi

Then, in frontend/: npm run gen:api. CI fails if either output is stale.
"""

from __future__ import annotations

import json

from backend.app.config import REPO_ROOT
from backend.app.main import app

OUT = REPO_ROOT / "frontend" / "src" / "api" / "openapi.json"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2)
    OUT.write_text(text + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
