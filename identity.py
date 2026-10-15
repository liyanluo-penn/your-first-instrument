"""Neon identity: absent credential = guest; invalid credential = error.

Adapted from jlumbroso/your-protected-notes (MIT, see LICENSE-auth.txt).
Ownership uses the verified subject, never an email or a tool argument.
"""
import os
import re
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from mcp.server.fastmcp import Context


@lru_cache(maxsize=4)
def _keys(url: str):
    return jwt.PyJWKClient(url, timeout=10)


def current_identity(ctx: Context) -> tuple[str | None, str | None]:
    request = getattr(ctx.request_context, "request", None)
    header = request.headers.get("authorization") if request is not None else None
    if header is None:
        return None, None
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise ValueError("Invalid Authorization header. Sign in again; nothing was saved as guest.")
    token = parts[1]
    if token == "guest-no-shelf":
        return None, None
    base = os.environ.get("NEON_AUTH_BASE_URL", "").rstrip("/")
    jwks = os.environ.get("NEON_AUTH_JWKS_URL") or (base + "/.well-known/jwks.json" if base else "")
    if not jwks:
        raise RuntimeError("Neon Auth is not configured. Set NEON_AUTH_BASE_URL before signing in.")
    legacy = re.search(r"/projects/([0-9a-fA-F-]+)/", jwks)
    audience = os.environ.get("STACK_PROJECT_ID") or (legacy.group(1) if legacy else None)
    origin = urlsplit(base)
    issuer = f"{origin.scheme}://{origin.netloc}" if base else None
    try:
        key = _keys(jwks).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token, key, algorithms=["EdDSA", "ES256", "RS256"],
            audience=audience, issuer=issuer,
            options={"verify_aud": bool(audience), "require": ["sub", "exp"]},
        )
        if not isinstance(claims["sub"], str) or not claims["sub"].strip():
            raise jwt.InvalidTokenError("Missing subject")
    except jwt.PyJWTError:
        raise ValueError("Invalid or expired sign-in. Reconnect; nothing was saved as guest.") from None
    return claims["sub"], claims.get("email")
