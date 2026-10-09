"""Phone-number login with a JWT (task C2, blueprint section 10). HS256, standard library only.

The demo uses a pre-seeded profile and no OTP (blueprint decision 10): anyone who knows a registered phone
number can log in as that farmer. Fine for a demo with invented profiles, not for real farmers' data.
FS_JWT_SECRET signs tokens; without it a random secret is made at start-up (tokens then end at restart).
The token goes in the Authorization header, never a cookie (no CSRF).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app import db

log = logging.getLogger("farmsight.auth")
TOKEN_DAYS = 7
_bearer = HTTPBearer(auto_error=False)
_secret: bytes | None = None


def secret() -> bytes:
    global _secret
    if _secret is None:
        configured = os.environ.get("FS_JWT_SECRET", "")
        if not configured:
            log.warning("FS_JWT_SECRET is not set: using a random secret, so logins end when the server restarts")
        _secret = configured.encode() or secrets.token_bytes(32)
    return _secret


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def make_token(farmer_id: str, now: float | None = None) -> str:
    issued = int(now if now is not None else time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = _b64(json.dumps({"sub": farmer_id, "iat": issued, "exp": issued + TOKEN_DAYS * 86400},
                              separators=(",", ":")).encode())
    signature = _b64(hmac.new(secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{signature}"


def read_token(token: str, now: float | None = None) -> str | None:
    """The farmer id, or None if the token is malformed, tampered with or expired."""
    try:
        header, payload, signature = token.split(".")
        expected = _b64(hmac.new(secret(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            return None
        if json.loads(_unb64(header)).get("alg") != "HS256":
            return None
        claims = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if claims.get("exp", 0) < (now if now is not None else time.time()):
        return None
    return claims.get("sub")


def optional_farmer(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict | None:  # noqa: B008
    if creds is None:
        return None
    farmer_id = read_token(creds.credentials)
    farmer = db.get_farmer(farmer_id) if farmer_id else None
    if farmer is None:
        raise HTTPException(401, "Please log in again.")
    return farmer


def current_farmer(farmer: dict | None = Depends(optional_farmer)) -> dict:  # noqa: B008
    if farmer is None:
        raise HTTPException(401, "Log in with your phone number first.")
    return farmer
