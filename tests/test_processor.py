import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db import SessionFactory
from app.models import Call, CallAnalysis, CallMetrics, CallStatus, Speaker, TranscriptSegment
from app.schemas import CallAnalysisData, TranscriptData, TranscriptSegmentData
from app.services.processor import CallProcessor


class FakeTranscriptionProvider:
    model_name = "fake-whisper"

    def transcribe(self, audio_path: Path) -> TranscriptData:
        assert audio_path.suffix == ".mp3"
        return TranscriptData(
            language="ru",
            segments=[
                TranscriptSegmentData(
                    speaker=Speaker.MANAGER, start_seconds=0, end_seconds=3, text="Здравствуйте"
                ),
                TranscriptSegmentData(
                    speaker=Speaker.CUSTOMER,
                    start_seconds=3.5,
                    end_seconds=7,
                    text="Для меня дорого",
                ),
            ],
        )


class FakeAnalysisProvider:
    model_name = "fake-local-llm"

    def analyze(self, transcript: TranscriptData) -> CallAnalysisData:
        return CallAnalysisData(
            summary="Клиент возразил по цене",
            topic="Стоимость",
            result="unknown",
            sentiment="neutral",
            objections=["Высокая стоимость"],
            agreements=[],
            next_action=None,
            quality_score=70,
        )


@pytest.mark.asyncio
async def test_processes_call_and_persists_derived_data(client, organization_id):
    created = client.post(
        "/api/v1/calls",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("call.mp3", b"ID3-fake-audio", "audio/mpeg")},
    ).json()

    async with SessionFactory() as session:
        processor = CallProcessor(FakeTranscriptionProvider(), FakeAnalysisProvider())
        call_id = uuid.UUID(created["id"])
        await processor.process(call_id, session)

    async with SessionFactory() as session:
        call = await session.get(Call, call_id)
        segments = list(await session.scalars(select(TranscriptSegment)))
        metrics = await session.get(CallMetrics, call_id)
        analysis = await session.get(CallAnalysis, call_id)

        assert call.status == CallStatus.COMPLETED
        assert len(segments) == 2
        assert metrics.manager_talk_ratio == pytest.approx(3 / 6.5, abs=0.0001)
        assert analysis.objections == ["Высокая стоимость"]
        assert analysis.model_name == "fake-local-llm"

    response = client.get(
        f"/api/v1/calls/{created['id']}", headers={"X-Organization-ID": organization_id}
    )
    assert response.status_code == 200
    assert response.json()["metrics"]["total_segments"] == 2
    assert response.json()["analysis"]["topic"] == "Стоимость"
