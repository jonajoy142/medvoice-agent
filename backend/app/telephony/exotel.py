from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from app.core.config import settings
from app.telephony.base import OutboundCallRequest, TelephonyCallResult, TelephonyProvider


@dataclass
class ExotelTelephonyProvider(TelephonyProvider):
    """Exotel adapter for outbound calls and status webhooks.

    Assumption: outbound Connect API accepts From, To, CallerId, Url form fields
    under /{account_sid}/Calls/connect.json. Verify exact account URL and audio
    streaming hooks with Exotel credentials before pilot use.
    """

    name: str = "exotel"

    def start_outbound_call(self, request: OutboundCallRequest) -> TelephonyCallResult:
        self._require_config()
        url = f"{settings.telephony_base_url.rstrip('/')}/{settings.telephony_account_sid}/Calls/connect.json"
        response = requests.post(
            url,
            auth=(settings.telephony_account_sid, settings.telephony_auth_token),
            data={
                "From": request.to_number,
                "To": settings.telephony_phone_number,
                "CallerId": settings.telephony_phone_number,
                "Url": request.callback_url,
            },
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        call = data.get("Call") if isinstance(data, dict) else None
        call_data = call if isinstance(call, dict) else data
        return TelephonyCallResult(
            provider=self.name,
            provider_call_id=str(call_data.get("Sid") or call_data.get("sid") or ""),
            status=str(call_data.get("Status") or call_data.get("status") or "queued"),
            raw=call_data,
        )

    def parse_status_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "provider": self.name,
            "provider_call_id": payload.get("CallSid") or payload.get("Sid") or payload.get("call_sid"),
            "status": payload.get("CallStatus") or payload.get("Status") or payload.get("status"),
            "duration_seconds": payload.get("CallDuration") or payload.get("Duration"),
            "raw": payload,
        }

    def _require_config(self) -> None:
        missing = [
            key
            for key, value in {
                "TELEPHONY_ACCOUNT_SID": settings.telephony_account_sid,
                "TELEPHONY_AUTH_TOKEN": settings.telephony_auth_token,
                "TELEPHONY_PHONE_NUMBER": settings.telephony_phone_number,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Exotel configuration: {', '.join(missing)}")
