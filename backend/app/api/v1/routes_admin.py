from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.telemetry import admin_queries

router = APIRouter(prefix="/admin", tags=["admin"])


def _hospital(x_hospital_id: str | None = Header(default=None)) -> str | None:
    return x_hospital_id


@router.get("/overview")
async def overview(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.overview(_hospital(x_hospital_id))


@router.get("/calls")
async def calls(
    x_hospital_id: str | None = Header(default=None),
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    return admin_queries.call_log(_hospital(x_hospital_id), search=search, status=status)


@router.get("/outcomes")
async def outcomes(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.outcomes(_hospital(x_hospital_id))


@router.get("/leads")
async def leads(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.leads(_hospital(x_hospital_id))


@router.get("/escalations")
async def escalations(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.escalations(_hospital(x_hospital_id))


@router.get("/knowledge-base")
async def knowledge_base(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.knowledge_base(_hospital(x_hospital_id))


@router.get("/quality")
async def quality(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.quality(_hospital(x_hospital_id))


@router.get("/consent")
async def consent(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.consent(_hospital(x_hospital_id))


@router.get("/audit")
async def audit(x_hospital_id: str | None = Header(default=None)):
    return admin_queries.audit(_hospital(x_hospital_id))
