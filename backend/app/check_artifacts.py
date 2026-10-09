"""Validates artifacts/ exactly as the backend does on startup.

Owner B runs this before committing artifacts; CI runs it on every pull request:

    python -m backend.app.check_artifacts
"""

from __future__ import annotations

import sys

from backend.app.artifacts import ArtifactError, load_store
from backend.app.config import get_settings


def main() -> int:
    directory = get_settings().artifacts_dir
    try:
        store = load_store(directory)
    except ArtifactError as e:
        print(e, file=sys.stderr)
        return 1
    m = store.meta
    label = "SYNTHETIC" if m.is_synthetic else "real"
    print(
        f"OK: {directory}\n"
        f"  {len(m.series)} series, {len(m.replay_cases)} replay cases, latest_as_of {m.latest_as_of}\n"
        f"  data_source={m.data_source} ({label})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
