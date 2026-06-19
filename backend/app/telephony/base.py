from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class OutboundCallRequest:
    to_number: str
    callback_url: str
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class TelephonyCallResult:
    provider: str
    provider_call_id: str
    status: str
    raw: dict[str, Any]


class TelephonyProvider(Protocol):
    name: str

    def start_outbound_call(self, request: OutboundCallRequest) -> TelephonyCallResult:
        ...

    def parse_status_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...
