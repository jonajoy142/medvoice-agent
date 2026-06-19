from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import requests
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.core.config import settings
from app.db.session import check_db_connection, db_session

security = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    staff_user_id: str
    supabase_user_id: str
    email: str
    full_name: str | None
    role: str
    hospital_id: str | None
    hospital_name: str | None
    hospital_status: str | None

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"


def require_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    supabase_user = verify_supabase_token(credentials.credentials)
    return load_staff_profile(str(supabase_user["id"]))


def require_roles(*roles: str):
    def _dependency(user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
        if user.role not in set(roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _dependency


def require_hospital_admin(user: CurrentUser = Depends(require_current_user)) -> CurrentUser:
    if user.role not in {"super_admin", "hospital_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hospital admin permission required")
    return user


def writable_hospital_id(user: CurrentUser, requested_hospital_id: str | None = None) -> str:
    if user.is_super_admin:
        if requested_hospital_id:
            return requested_hospital_id
        if user.hospital_id:
            return user.hospital_id
        raise HTTPException(status_code=400, detail="hospital_id is required for super admin write operations")
    if not user.hospital_id:
        raise HTTPException(status_code=403, detail="No active hospital membership")
    if requested_hospital_id and requested_hospital_id != user.hospital_id:
        raise HTTPException(status_code=403, detail="Cannot access another hospital")
    return user.hospital_id


def readable_hospital_filter(user: CurrentUser, requested_hospital_id: str | None = None) -> tuple[str, dict[str, Any]]:
    if user.is_super_admin:
        return ("WHERE hospital_id = :hospital_id", {"hospital_id": requested_hospital_id}) if requested_hospital_id else ("", {})
    hospital_id = writable_hospital_id(user, requested_hospital_id)
    return "WHERE hospital_id = :hospital_id", {"hospital_id": hospital_id}


def verify_supabase_token(access_token: str) -> dict[str, Any]:
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(status_code=503, detail="Sign-in is not configured for this deployment")
    response = requests.get(
        f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
        headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if response.status_code in {401, 403}:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if response.status_code >= 400:
        raise HTTPException(status_code=503, detail="Could not verify your session")
    data = response.json()
    if not isinstance(data, dict) or not data.get("id"):
        raise HTTPException(status_code=401, detail="Invalid session")
    return data


def load_staff_profile(supabase_user_id: str) -> CurrentUser:
    if not check_db_connection():
        raise HTTPException(status_code=503, detail="Workspace data is not configured")
    with db_session() as db:
        row = db.execute(
            text(
                """
                SELECT su.id, su.supabase_user_id, su.email, su.full_name, su.role, su.status,
                       su.hospital_id, h.name AS hospital_name, h.status AS hospital_status
                FROM staff_users su
                LEFT JOIN hospitals h ON h.id = su.hospital_id
                WHERE su.supabase_user_id = :supabase_user_id
                LIMIT 1
                """
            ),
            {"supabase_user_id": supabase_user_id},
        ).mappings().first()
    if not row or row["status"] != "active":
        raise HTTPException(status_code=403, detail="No active MedVoice staff membership")
    if row["role"] != "super_admin" and row["hospital_status"] not in {"active", "trialing", None}:
        raise HTTPException(status_code=403, detail="Hospital account is not active")
    return CurrentUser(
        staff_user_id=str(row["id"]),
        supabase_user_id=str(row["supabase_user_id"]),
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        hospital_id=str(row["hospital_id"]) if row["hospital_id"] else None,
        hospital_name=row["hospital_name"],
        hospital_status=row["hospital_status"],
    )


def assert_role(user: CurrentUser, allowed: Iterable[str]) -> None:
    if user.role not in set(allowed):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
