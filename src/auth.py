"""
API Key Authentication — CareerLens Phase 4.

Usage:
    Protect an endpoint by adding:
        api_key: str = Depends(verify_api_key)

Config (via .env):
    API_KEYS   — comma-separated list of valid keys, e.g. "key1,key2"
                 Set to "*" (or leave blank) to disable auth in local dev.
    AUTH_ENABLED — "true" | "false" (default: "true")
                  Shorthand override to disable auth without touching API_KEYS.

Header expected from clients:
    X-API-Key: <your-key>
"""

import logging
import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Comma-separated list of accepted API keys.
# Wildcards ("*") or an empty string → auth is disabled (dev/test mode).
_raw_keys: str = os.getenv("API_KEYS", "")

# Hard override — set AUTH_ENABLED=false to skip auth altogether.
_auth_enabled_env: str = os.getenv("AUTH_ENABLED", "true").strip().lower()
AUTH_ENABLED: bool = _auth_enabled_env not in ("false", "0", "no")

# Build the set of valid keys; strip whitespace and empty strings.
VALID_API_KEYS: set[str] = {
    k.strip() for k in _raw_keys.split(",") if k.strip() and k.strip() != "*"
}

# If the env var is "*" or empty, disable auth regardless of AUTH_ENABLED.
if not VALID_API_KEYS or _raw_keys.strip() == "*":
    AUTH_ENABLED = False

if AUTH_ENABLED:
    logger.info(
        "API key auth ENABLED — %d key(s) configured.", len(VALID_API_KEYS)
    )
else:
    logger.warning(
        "API key auth DISABLED — all requests are accepted. "
        "Set API_KEYS and AUTH_ENABLED=true for production."
    )

# ---------------------------------------------------------------------------
# FastAPI security scheme (shows up in /docs Swagger UI)
# ---------------------------------------------------------------------------

_api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,   # We handle the error ourselves for better messages
    description="Pass your CareerLens API key in the X-API-Key header.",
)


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
) -> str | None:
    """
    FastAPI dependency — validates the X-API-Key header.

    - If AUTH_ENABLED is False (dev mode) → always passes through.
    - If the key is missing or invalid → raises HTTP 403.
    - If valid → returns the key (can be used downstream if needed).
    """
    if not AUTH_ENABLED:
        return None   # Auth disabled — allow all

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Missing API key. "
                "Include your key in the X-API-Key request header."
            ),
        )

    if api_key not in VALID_API_KEYS:
        logger.warning("Rejected request with invalid API key: %r", api_key[:8] + "…")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
