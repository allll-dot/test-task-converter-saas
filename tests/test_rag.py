import uuid

import pytest
from sqlalchemy import select

from app.db import SessionFactory
from app.models import Call, Speaker, TranscriptChunk, TranscriptSegment
from app.rag import get_rag_service
from app.schemas import AskResponse, RagSource
from app.services.rag import TranscriptIndexer, build_chunks


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), *([0.0] * 767)] for text in texts]


class FakeRagService:
    def __init__(self) -> None:
        self.organization_id: uuid.UUID | None = None

    async def ask(self, question, organization_id, session, call_id=None, limit=5):
        self.organization_id = organization_id
        return AskResponse(
            answer="Клиента записали на консультацию.",
            sources=[
                RagSource(
                    call_id=call_id or uuid.uuid4(),
                    start_seconds=12,
                    end_seconds=18,
                    text="manager: Записываю вас на пятницу",
                )
            ],
        )


def test_builds_timestamped_chunks():
    segments = [
        TranscriptSegment(
            organization_id=uuid.uuid4(),
            call_id=uuid.uuid4(),
            speaker=Speaker.MANAGER,
            start_seconds=0,
            end_seconds=2,
            text="Здравствуйте",
        ),
        TranscriptSegment(
            organization_id=uuid.uuid4(),
            call_id=uuid.uuid4(),
            speaker=Speaker.CUSTOMER,
            start_seconds=2,
            end_seconds=5,
            text="Хочу записаться",
        ),
    ]

    chunks = build_chunks(segments)

    assert len(chunks) == 1
    assert chunks[0].start_seconds == 0
    assert chunks[0].end_seconds == 5
    assert "customer: Хочу записаться" in chunks[0].text


@pytest.mark.asyncio
async def test_indexes_transcript_with_local_embeddings(client, organization_id):
    call_id = uuid.uuid4()
    organization_uuid = uuid.UUID(organization_id)
    async with SessionFactory() as session:
        session.add(
            Call(
                id=call_id,
                organization_id=organization_uuid,
                original_filename="call.mp3",
                audio_path="call.mp3",
            )
        )
        session.add(
            TranscriptSegment(
                organization_id=organization_uuid,
                call_id=call_id,
                speaker=Speaker.CUSTOMER,
                start_seconds=4,
                end_seconds=9,
                text="Запишите меня на приём",
            )
        )
        await session.commit()
        await TranscriptIndexer(FakeEmbeddingProvider()).index(call_id, session)

    async with SessionFactory() as session:
        chunks = list(await session.scalars(select(TranscriptChunk)))
    assert len(chunks) == 1
    assert chunks[0].organization_id == organization_uuid
    assert chunks[0].start_seconds == 4
    assert len(chunks[0].embedding) == 768


def test_ask_endpoint_returns_timestamped_sources(client, organization_id):
    fake = FakeRagService()
    from app.main import app

    app.dependency_overrides[get_rag_service] = lambda: fake
    call_id = uuid.uuid4()
    try:
        response = client.post(
            "/api/v1/analytics/ask",
            headers={"X-Organization-ID": organization_id},
            json={"question": "Кого записали на приём?", "call_id": str(call_id)},
        )
    finally:
        app.dependency_overrides.pop(get_rag_service, None)

    assert response.status_code == 200
    assert fake.organization_id == uuid.UUID(organization_id)
    assert response.json()["sources"][0] == {
        "call_id": str(call_id),
        "start_seconds": 12.0,
        "end_seconds": 18.0,
        "text": "manager: Записываю вас на пятницу",
    }
