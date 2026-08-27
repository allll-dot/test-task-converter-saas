import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import tenant_id
from app.db import get_session
from app.models import AppointmentStatus, Call, CallAnalysis, CallMetrics, CallStatus
from app.schemas import StatisticsResponse

router = APIRouter()


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
