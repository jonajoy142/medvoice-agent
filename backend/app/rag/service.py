from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from app.core.config import settings
from app.db.session import db_session
from app.embeddings.factory import get_embedding_provider
from app.guardrails import safety_guardrails


@dataclass(frozen=True)
class RAGResult:
    answer: str
    confidence: float
    citations: list[dict[str, Any]]
    content_gap: bool = False


class KnowledgeBaseService:
    def ingest_text(self, *, hospital_id: str, title: str, body: str, source_uri: str | None = None) -> str:
        if safety_guardrails.has_prompt_injection(body):
            raise ValueError("Knowledge-base document contains prompt-injection style text and was blocked.")
        embedding = get_embedding_provider().embed(body)
        with db_session() as db:
            row = db.execute(
                text(
                    """
                    INSERT INTO knowledge_base_documents (hospital_id, title, source_uri, status, body, embedding)
                    VALUES (:hospital_id, :title, :source_uri, 'active', :body, :embedding)
                    RETURNING id
                    """
                ),
                {
                    "hospital_id": hospital_id,
                    "title": title,
                    "source_uri": source_uri,
                    "body": body,
                    "embedding": embedding,
                },
            ).first()
            return str(row[0])

    def answer(self, *, hospital_id: str, question: str) -> RAGResult:
        embedding = get_embedding_provider().embed(question)
        with db_session() as db:
            rows = db.execute(
                text(
                    """
                    SELECT id, title, body, 1 - (embedding <=> :embedding) AS confidence
                    FROM knowledge_base_documents
                    WHERE hospital_id = :hospital_id AND status = 'active' AND embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding
                    LIMIT 3
                    """
                ),
                {"hospital_id": hospital_id, "embedding": embedding},
            ).mappings().all()
        if not rows:
            return RAGResult("", 0.0, [], True)
        best = rows[0]
        confidence = float(best["confidence"] or 0.0)
        if confidence < settings.rag_confidence_threshold:
            return RAGResult("", confidence, [_citation(row) for row in rows], True)
        answer = str(best["body"] or "").strip()
        decision = safety_guardrails.evaluate_rag(confidence=confidence, answer=answer)
        if not decision.allowed:
            return RAGResult(decision.safe_response or "", confidence, [_citation(row) for row in rows], True)
        return RAGResult(answer, confidence, [_citation(row) for row in rows])


def _citation(row: Any) -> dict[str, Any]:
    return {"document_id": str(row["id"]), "title": row["title"], "confidence": float(row["confidence"] or 0.0)}


knowledge_base_service = KnowledgeBaseService()
