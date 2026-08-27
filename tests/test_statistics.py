import uuid

import pytest

from app.db import SessionFactory
from app.models import AppointmentStatus, Call, CallAnalysis, CallMetrics, CallStatus, Organization


@pytest.mark.asyncio
async def test_returns_tenant_isolated_aggregated_statistics(client, organization_id):
    own_id = uuid.UUID(organization_id)
    other_id = uuid.uuid4()

    async with SessionFactory() as session:
        session.add(Organization(id=other_id, name="Other company"))
        completed = Call(
            organization_id=own_id,
            original_filename="completed.mp3",
            audio_path="/tmp/completed.mp3",
            status=CallStatus.COMPLETED,
        )
        failed = Call(
            organization_id=own_id,
            original_filename="failed.mp3",
            audio_path="/tmp/failed.mp3",
            status=CallStatus.FAILED,
        )
        foreign = Call(
            organization_id=other_id,
            original_filename="foreign.mp3",
            audio_path="/tmp/foreign.mp3",
            status=CallStatus.COMPLETED,
        )
        session.add_all([completed, failed, foreign])
        await session.flush()
        session.add_all(
            [
                CallMetrics(
                    call_id=completed.id,
                    organization_id=own_id,
                    duration_seconds=120,
                    manager_speech_seconds=50,
                    customer_speech_seconds=60,
                    unknown_speech_seconds=0,
                    manager_talk_ratio=0.45,
                    total_segments=20,
                ),
                CallAnalysis(
                    call_id=completed.id,
                    organization_id=own_id,
                    summary="Продажа завершена",
                    topic="Продажа",
                    result="sale",
                    sentiment="positive",
                    objections=[],
                    agreements=["Оформить заказ"],
                    next_action=None,
                    appointment_status=AppointmentStatus.BOOKED,
                    appointment_datetime="2026-08-30 15:00",
                    appointment_service="Первичный приём",
                    quality_score=80,
                    model_name="fake",
                    prompt_version="v1",
                ),
                CallMetrics(
                    call_id=foreign.id,
                    organization_id=other_id,
                    duration_seconds=999,
                    manager_speech_seconds=400,
                    customer_speech_seconds=500,
                    unknown_speech_seconds=0,
                    manager_talk_ratio=0.44,
                    total_segments=100,
                ),
                CallAnalysis(
                    call_id=foreign.id,
                    organization_id=other_id,
                    summary="Чужой звонок",
                    topic="Другое",
                    result="rejected",
                    sentiment="negative",
                    objections=[],
                    agreements=[],
                    next_action=None,
                    appointment_status=AppointmentStatus.CANCELLED,
                    appointment_datetime=None,
                    appointment_service="Чужая услуга",
                    quality_score=10,
                    model_name="fake",
                    prompt_version="v1",
                ),
            ]
        )
        await session.commit()

    response = client.get(
        "/api/v1/statistics",
        headers={"X-Organization-ID": organization_id},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_calls": 2,
        "completed_calls": 1,
        "failed_calls": 1,
        "average_duration_seconds": 120.0,
        "average_quality_score": 80.0,
        "statuses": {"completed": 1, "failed": 1},
        "results": {"sale": 1},
        "appointments": {"booked": 1},
        "booking_conversion_rate": 1.0,
    }
