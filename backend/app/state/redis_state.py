from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class RedisSessionState:
    prefix: str = "medvoice:session"
    ttl_seconds: int = 60 * 60 * 8

    def _client(self):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("redis package is required for Redis session state.") from exc
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def get(self, session_id: str) -> dict[str, Any] | None:
        value = self._client().get(self._key(session_id))
        return json.loads(value) if value else None

    def set(self, session_id: str, data: dict[str, Any]) -> None:
        self._client().setex(self._key(session_id), self.ttl_seconds, json.dumps(data))

    def update(self, session_id: str, data: dict[str, Any]) -> dict[str, Any]:
        current = self.get(session_id) or {}
        current.update(data)
        self.set(session_id, current)
        return current

    def _key(self, session_id: str) -> str:
        return f"{self.prefix}:{session_id}"
