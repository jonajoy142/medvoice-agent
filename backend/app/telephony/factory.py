from __future__ import annotations

from app.core.config import settings
from app.telephony.base import TelephonyProvider
from app.telephony.exotel import ExotelTelephonyProvider


def get_telephony_provider() -> TelephonyProvider:
    provider = settings.telephony_provider.lower()
    if provider == "exotel":
        return ExotelTelephonyProvider()
    raise RuntimeError(f"Telephony provider {provider!r} is configured but not implemented yet.")
