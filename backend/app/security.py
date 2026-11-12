import logging
import secrets

from fastapi import Header, HTTPException, status

from app.config import get_settings

logger = logging.getLogger(__name__)


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    FastAPI dependency protecting write endpoints.

    - If API_KEY is not configured, access is allowed (development convenience).
    - Otherwise the caller must send a matching `X-API-Key` header.
    Comparison is constant-time to avoid leaking the key through timing.
    """
    expected = get_settings().api_key
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
