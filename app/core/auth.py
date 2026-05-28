from fastapi import Header, HTTPException

from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """
    Optional API-key gate for patient-sensitive endpoints.
    Disabled by default to preserve existing local flows.
    """
    if not settings.require_api_key:
        return

    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API key protection is enabled but MEDVOICE_API_KEY is not set.")

    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key.")
