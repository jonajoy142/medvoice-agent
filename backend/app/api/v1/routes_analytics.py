"""Analytics API endpoints for business metrics and revenue."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import text

from app.core.rbac import require_current_user, writable_hospital_id
from app.db.session import db_session

router = APIRouter(tags=["analytics"])


class AnalyticsMetrics(BaseModel):
    """Analytics metrics response."""
    total_calls: int
    connected_calls: int
    successful_calls: int
    converted_calls: int
    conversion_rate: float
    total_revenue: float
    average_order_value: float
    average_call_duration: float
    ai_resolution_rate: float
    human_transfer_rate: float
    failure_rate: float
    average_response_latency: float
    p50_latency: float
    p95_latency: float
    total_ai_cost: float
    ai_cost_per_call: float
    ai_cost_per_minute: float


class CallAnalytics(BaseModel):
    """Call analytics response."""
    call_id: str
    customer_phone: str
    duration_seconds: int
    status: str
    outcome: str
    revenue: Optional[float]
    latency_ms: Optional[int]
    language: str
    created_at: datetime


@router.get("/metrics", response_model=AnalyticsMetrics)
async def get_analytics_metrics(
    hospital_id: str = Depends(writable_hospital_id),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    _: None = Depends(require_current_user)
):
    """Get comprehensive analytics metrics for a hospital."""
    try:
        with db_session() as db:
            # Default to last 30 days if no date range provided
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Total calls
            total_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0
            
            # Connected calls (not missed)
            connected_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND missed = false
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0
            
            # Successful calls (completed, not escalated)
            successful_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND status = 'completed'
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0
            
            # Converted calls (with revenue or appointment booked)
            converted_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND (revenue_estimate > 0 OR final_bill_amount > 0 OR appointment_status IN ('confirmed', 'completed'))
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0
            
            # Conversion rate
            conversion_rate = (converted_calls / connected_calls * 100) if connected_calls > 0 else 0.0
            
            # Total revenue
            total_revenue = db.execute(
                text("""
                    SELECT COALESCE(SUM(final_bill_amount), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # Average order value
            avg_order_value = db.execute(
                text("""
                    SELECT COALESCE(AVG(final_bill_amount), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND final_bill_amount > 0
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # Average call duration
            avg_duration = db.execute(
                text("""
                    SELECT COALESCE(AVG(duration_seconds), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND duration_seconds IS NOT NULL
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # AI resolution rate (calls answered by AI that completed successfully)
            ai_resolution_rate = db.execute(
                text("""
                    SELECT COALESCE(
                        100.0 * COUNT(*) FILTER (WHERE answered_by_ai = true AND status = 'completed') / 
                        NULLIF(COUNT(*) FILTER (WHERE answered_by_ai = true), 0), 
                        0
                    ) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # Human transfer rate
            human_transfer_rate = db.execute(
                text("""
                    SELECT COALESCE(
                        100.0 * COUNT(*) FILTER (WHERE status = 'escalated') / 
                        NULLIF(COUNT(*), 0), 
                        0
                    ) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # Failure rate
            failure_rate = db.execute(
                text("""
                    SELECT COALESCE(
                        100.0 * COUNT(*) FILTER (WHERE status IN ('failed', 'error')) / 
                        NULLIF(COUNT(*), 0), 
                        0
                    ) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # Average response latency
            avg_latency = db.execute(
                text("""
                    SELECT COALESCE(AVG(response_latency_ms), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND response_latency_ms IS NOT NULL
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # P50 latency (median)
            p50_latency = db.execute(
                text("""
                    SELECT COALESCE(
                        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_latency_ms),
                        0
                    ) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND response_latency_ms IS NOT NULL
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # P95 latency
            p95_latency = db.execute(
                text("""
                    SELECT COALESCE(
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_latency_ms),
                        0
                    ) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND response_latency_ms IS NOT NULL
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # AI cost (from usage_events if available, otherwise estimate)
            total_ai_cost = db.execute(
                text("""
                    SELECT COALESCE(SUM(quantity), 0) FROM usage_events 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0.0
            
            # AI cost per call
            ai_cost_per_call = (total_ai_cost / connected_calls) if connected_calls > 0 else 0.0
            
            # AI cost per minute
            total_minutes = (db.execute(
                text("""
                    SELECT COALESCE(SUM(duration_seconds), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            ).scalar() or 0) / 60.0
            ai_cost_per_minute = (total_ai_cost / total_minutes) if total_minutes > 0 else 0.0
            
            return AnalyticsMetrics(
                total_calls=total_calls,
                connected_calls=connected_calls,
                successful_calls=successful_calls,
                converted_calls=converted_calls,
                conversion_rate=round(conversion_rate, 2),
                total_revenue=round(float(total_revenue), 2),
                average_order_value=round(float(avg_order_value), 2),
                average_call_duration=round(avg_duration, 2),
                ai_resolution_rate=round(ai_resolution_rate, 2),
                human_transfer_rate=round(human_transfer_rate, 2),
                failure_rate=round(failure_rate, 2),
                average_response_latency=round(avg_latency, 2),
                p50_latency=round(p50_latency, 2),
                p95_latency=round(p95_latency, 2),
                total_ai_cost=round(float(total_ai_cost), 2),
                ai_cost_per_call=round(ai_cost_per_call, 2),
                ai_cost_per_minute=round(ai_cost_per_minute, 2),
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calls", response_model=List[CallAnalytics])
async def get_call_analytics(
    hospital_id: str = Depends(writable_hospital_id),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: None = Depends(require_current_user)
):
    """Get recent call analytics."""
    try:
        with db_session() as db:
            query = text("""
                SELECT 
                    id as call_id,
                    caller_phone as customer_phone,
                    duration_seconds,
                    status,
                    outcome,
                    final_bill_amount as revenue,
                    response_latency_ms as latency_ms,
                    language,
                    created_at
                FROM calls 
                WHERE hospital_id = :hospital_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """)
            result = db.execute(query, {"hospital_id": hospital_id, "limit": limit, "offset": offset})
            return [dict(row._mapping) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue")
async def get_revenue_analytics(
    hospital_id: str = Depends(writable_hospital_id),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    _: None = Depends(require_current_user)
):
    """Get revenue analytics broken down by time period."""
    try:
        with db_session() as db:
            if not end_date:
                end_date = datetime.utcnow()
            if not start_date:
                start_date = end_date - timedelta(days=30)
            
            # Daily revenue
            daily_revenue = db.execute(
                text("""
                    SELECT 
                        DATE(created_at) as date,
                        COALESCE(SUM(final_bill_amount), 0) as revenue,
                        COUNT(*) as calls
                    FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at BETWEEN :start_date AND :end_date
                    AND final_bill_amount IS NOT NULL
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """),
                {"hospital_id": hospital_id, "start_date": start_date, "end_date": end_date}
            )
            
            return {
                "hospital_id": hospital_id,
                "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "daily_breakdown": [dict(row._mapping) for row in daily_revenue],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-stats")
async def get_live_stats(
    hospital_id: str = Depends(writable_hospital_id),
    _: None = Depends(require_current_user)
):
    """Get live statistics for active calls."""
    try:
        with db_session() as db:
            # Active calls (in last 5 minutes)
            active_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at > NOW() - INTERVAL '5 minutes'
                    AND status IN ('in_progress', 'connected')
                """),
                {"hospital_id": hospital_id}
            ).scalar() or 0
            
            # Calls in last hour
            recent_calls = db.execute(
                text("""
                    SELECT COUNT(*) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND created_at > NOW() - INTERVAL '1 hour'
                """),
                {"hospital_id": hospital_id}
            ).scalar() or 0
            
            # Revenue today
            today_revenue = db.execute(
                text("""
                    SELECT COALESCE(SUM(final_bill_amount), 0) FROM calls 
                    WHERE hospital_id = :hospital_id 
                    AND DATE(created_at) = CURRENT_DATE
                """),
                {"hospital_id": hospital_id}
            ).scalar() or 0.0
            
            return {
                "hospital_id": hospital_id,
                "active_calls": active_calls,
                "calls_last_hour": recent_calls,
                "revenue_today": round(float(today_revenue), 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
