import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import tenant_id
from app.db import get_session
from app.models import AppointmentStatus, Call, CallAnalysis, CallMetrics, CallStatus
from app.schemas import DashboardCallResponse, StatisticsResponse

router = APIRouter()


@router.get("/api/v1/dashboard/calls", response_model=list[DashboardCallResponse])
async def get_dashboard_calls(
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[DashboardCallResponse]:
    rows = await session.execute(
        select(Call, CallAnalysis, CallMetrics)
        .outerjoin(CallAnalysis, CallAnalysis.call_id == Call.id)
        .outerjoin(CallMetrics, CallMetrics.call_id == Call.id)
        .where(Call.organization_id == organization_id)
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    return [
        DashboardCallResponse(
            id=call.id,
            original_filename=call.original_filename,
            status=call.status,
            created_at=call.created_at,
            topic=analysis.topic if analysis else None,
            result=analysis.result if analysis else None,
            appointment_status=analysis.appointment_status if analysis else None,
            appointment_datetime=analysis.appointment_datetime if analysis else None,
            appointment_service=analysis.appointment_service if analysis else None,
            quality_score=analysis.quality_score if analysis else None,
            duration_seconds=metrics.duration_seconds if metrics else None,
        )
        for call, analysis, metrics in rows
    ]


@router.get("/api/v1/statistics", response_model=StatisticsResponse)
async def get_statistics(
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StatisticsResponse:
    status_rows = await session.execute(
        select(Call.status, func.count(Call.id))
        .where(Call.organization_id == organization_id)
        .group_by(Call.status)
    )
    statuses = {status.value: count for status, count in status_rows}

    averages = await session.execute(
        select(
            func.avg(CallMetrics.duration_seconds),
            func.avg(CallAnalysis.quality_score),
        )
        .select_from(Call)
        .join(CallMetrics, CallMetrics.call_id == Call.id)
        .join(CallAnalysis, CallAnalysis.call_id == Call.id)
        .where(
            Call.organization_id == organization_id,
            Call.status == CallStatus.COMPLETED,
        )
    )
    average_duration, average_quality = averages.one()

    result_rows = await session.execute(
        select(CallAnalysis.result, func.count(CallAnalysis.call_id))
        .join(Call, Call.id == CallAnalysis.call_id)
        .where(
            Call.organization_id == organization_id,
            Call.status == CallStatus.COMPLETED,
        )
        .group_by(CallAnalysis.result)
    )
    results = {result: count for result, count in result_rows}

    appointment_rows = await session.execute(
        select(CallAnalysis.appointment_status, func.count(CallAnalysis.call_id))
        .join(Call, Call.id == CallAnalysis.call_id)
        .where(
            Call.organization_id == organization_id,
            Call.status == CallStatus.COMPLETED,
        )
        .group_by(CallAnalysis.appointment_status)
    )
    appointments = {status.value: count for status, count in appointment_rows}
    booking_successes = appointments.get(AppointmentStatus.BOOKED.value, 0) + appointments.get(
        AppointmentStatus.RESCHEDULED.value, 0
    )
    booking_attempts = (
        booking_successes
        + appointments.get(AppointmentStatus.NOT_BOOKED.value, 0)
        + appointments.get(AppointmentStatus.CANCELLED.value, 0)
    )

    return StatisticsResponse(
        total_calls=sum(statuses.values()),
        completed_calls=statuses.get(CallStatus.COMPLETED.value, 0),
        failed_calls=statuses.get(CallStatus.FAILED.value, 0),
        average_duration_seconds=float(average_duration) if average_duration is not None else None,
        average_quality_score=float(average_quality) if average_quality is not None else None,
        statuses=statuses,
        results=results,
        appointments=appointments,
        booking_conversion_rate=(
            round(booking_successes / booking_attempts, 4) if booking_attempts else None
        ),
    )
