"""Shared pytest setup: tests never touch the real runtime database (var/farmsight.sqlite)."""

import os

os.environ["FS_DB_PATH"] = ":memory:"
os.environ.setdefault("FS_JWT_SECRET", "test-secret")
