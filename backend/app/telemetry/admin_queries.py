from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.session import check_db_connection, db_session


def _empty_overview() -> dict[str, Any]:
    return {
        "data_source": "database" if settings.use_database else "database_not_configured",
        "calls": {"today": 0, "week": 0, "month": 0},
        "rates": {"completed": 0.0, "failed": 0.0, "escalated": 0.0},
        "average_handle_time_seconds": 0,
        "busiest_hours": [],
        "trend": [],
    }


@dataclass
class AdminQueries:
    def overview(self, hospital_id: str | None = None) -> dict[str, Any]:
        if not check_db_connection():
            return _empty_overview()
        where, params = _hospital_filter(hospital_id)
        with db_session() as db:
            counts = db.execute(
                text(
                    f"""
                    SELECT
                      count(*) FILTER (WHERE started_at >= date_trunc('day', now())) AS today,
                      count(*) FILTER (WHERE started_at >= date_trunc('week', now())) AS week,
                      count(*) FILTER (WHERE started_at >= date_trunc('month', now())) AS month,
                      count(*) AS total,
                      count(*) FILTER (WHERE status = 'completed') AS completed,
                      count(*) FILTER (WHERE status = 'failed') AS failed,
                      count(*) FILTER (WHERE status = 'escalated') AS escalated,
                      coalesce(avg(duration_seconds), 0)::int AS avg_handle_time
                    FROM calls
                    {where}
                    """
                ),
                params,
            ).mappings().one()
            busiest = db.execute(
                text(
                    f"""
                    SELECT extract(hour from started_at)::int AS hour, count(*)::int AS calls
                    FROM calls
                    {where}
                    GROUP BY 1 ORDER BY calls DESC, hour ASC LIMIT 6
                    """
                ),
                params,
            ).mappings().all()
            trend = db.execute(
                text(
                    f"""
                    SELECT date_trunc('day', started_at)::date AS day, count(*)::int AS calls
                    FROM calls
                    {where}
                    GROUP BY 1 ORDER BY day DESC LIMIT 30
                    """
                ),
                params,
            ).mappings().all()
        total = int(counts["total"] or 0)
        return {
            "data_source": "database",
            "calls": {"today": int(counts["today"] or 0), "week": int(counts["week"] or 0), "month": int(counts["month"] or 0)},
            "rates": {
                "completed": _rate(counts["completed"], total),
                "failed": _rate(counts["failed"], total),
                "escalated": _rate(counts["escalated"], total),
            },
            "average_handle_time_seconds": int(counts["avg_handle_time"] or 0),
            "busiest_hours": [dict(row) for row in busiest],
            "trend": [dict(row) for row in reversed(trend)],
        }

    def call_log(self, hospital_id: str | None = None, search: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        if not check_db_connection():
            return []
        clauses, params = _base_clauses(hospital_id)
        if status:
            clauses.append("c.status = :status")
            params["status"] = status
        if search:
            clauses.append("(c.patient_opid ILIKE :search OR c.workflow_type ILIKE :search OR c.outcome ILIKE :search)")
            params["search"] = f"%{search}%"
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        with db_session() as db:
            rows = db.execute(
                text(
                    f"""
                    SELECT c.id, c.patient_opid, c.workflow_type, c.outcome, c.status,
                           c.duration_seconds, c.started_at, cs.intent, cs.discussed, cs.decision
                    FROM calls c
                    LEFT JOIN call_summaries cs ON cs.call_id = c.id
                    {where}
                    ORDER BY c.started_at DESC
                    LIMIT 100
                    """
                ),
                params,
            ).mappings().all()
        return [_jsonable(dict(row)) for row in rows]

    def outcomes(self, hospital_id: str | None = None) -> list[dict[str, Any]]:
        if not check_db_connection():
            return []
        where, params = _hospital_filter(hospital_id, alias="c")
        with db_session() as db:
            rows = db.execute(
                text(
                    f"""
                    SELECT c.id AS call_id, c.workflow_type, c.outcome, c.status, c.started_at,
                           cs.decision, cs.follow_up_needed
                    FROM calls c
                    LEFT JOIN call_summaries cs ON cs.call_id = c.id
                    {where}
                    ORDER BY c.started_at DESC LIMIT 100
                    """
                ),
                params,
            ).mappings().all()
        return [_jsonable(dict(row)) for row in rows]

    def leads(self, hospital_id: str | None = None) -> list[dict[str, Any]]:
        return self._simple_list("leads", hospital_id, "created_at")

    def escalations(self, hospital_id: str | None = None) -> list[dict[str, Any]]:
        return self._simple_list("escalations", hospital_id, "created_at")

    def knowledge_base(self, hospital_id: str | None = None) -> dict[str, Any]:
        if not check_db_connection():
            return {"documents": [], "content_gaps": []}
        where, params = _hospital_filter(hospital_id)
        with db_session() as db:
            docs = db.execute(
                text(
                    f"""
                    SELECT id, title, source_uri, storage_path, status, content_gap_count, created_at, updated_at
                    FROM knowledge_base_documents
                    {where}
                    ORDER BY updated_at DESC LIMIT 100
                    """
                ),
                params,
            ).mappings().all()
        gaps = [dict(row) for row in docs if int(row.get("content_gap_count") or 0) > 0]
        return {"documents": [_jsonable(dict(row)) for row in docs], "content_gaps": [_jsonable(row) for row in gaps]}

    def quality(self, hospital_id: str | None = None) -> dict[str, Any]:
        if not check_db_connection():
            return {"latency": [], "intent_confidence": [], "unsafe_flags": 0, "escalation_accuracy": None}
        where, params = _hospital_filter(hospital_id, alias="c")
        with db_session() as db:
            latency = db.execute(
                text(
                    f"""
                    SELECT c.id AS call_id,
                           avg(ct.latency_ms)::int AS avg_turn_latency_ms,
                           avg(i.confidence)::float AS avg_intent_confidence
                    FROM calls c
                    LEFT JOIN conversation_turns ct ON ct.call_id = c.id
                    LEFT JOIN intents i ON i.call_id = c.id
                    {where}
                    GROUP BY c.id, c.started_at ORDER BY c.started_at DESC LIMIT 50
                    """
                ),
                params,
            ).mappings().all()
            unsafe = db.execute(
                text(f"SELECT count(*)::int AS count FROM escalations e {_where_alias(hospital_id, 'e')}") , params
            ).scalar_one()
        return {"latency": [_jsonable(dict(row)) for row in latency], "unsafe_flags": int(unsafe or 0), "escalation_accuracy": None}

    def audit(self, hospital_id: str | None = None) -> list[dict[str, Any]]:
        return self._simple_list("audit_logs", hospital_id, "created_at")

    def consent(self, hospital_id: str | None = None) -> list[dict[str, Any]]:
        return self._simple_list("consent_records", hospital_id, "captured_at")

    def _simple_list(self, table: str, hospital_id: str | None, order_column: str) -> list[dict[str, Any]]:
        if not check_db_connection():
            return []
        where, params = _hospital_filter(hospital_id)
        with db_session() as db:
            rows = db.execute(text(f"SELECT * FROM {table} {where} ORDER BY {order_column} DESC LIMIT 100"), params).mappings().all()
        return [_jsonable(dict(row)) for row in rows]


def _rate(value: Any, total: int) -> float:
    return round((float(value or 0) / total) * 100, 2) if total else 0.0


def _hospital_filter(hospital_id: str | None, alias: str | None = None) -> tuple[str, dict[str, Any]]:
    if not hospital_id:
        return "", {}
    prefix = f"{alias}." if alias else ""
    return f"WHERE {prefix}hospital_id = :hospital_id", {"hospital_id": hospital_id}


def _base_clauses(hospital_id: str | None) -> tuple[list[str], dict[str, Any]]:
    if hospital_id:
        return ["c.hospital_id = :hospital_id"], {"hospital_id": hospital_id}
    return [], {}


def _where_alias(hospital_id: str | None, alias: str) -> str:
    return f"WHERE {alias}.hospital_id = :hospital_id" if hospital_id else ""


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            result[key] = value.astimezone(timezone.utc).isoformat()
        else:
            result[key] = str(value) if value.__class__.__name__ == "UUID" else value
    return result


admin_queries = AdminQueries()
