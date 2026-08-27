import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TranscriptChunk, TranscriptSegment
from app.schemas import AskResponse, RagSource
from app.services.contracts import EmbeddingProvider, RagAnswerProvider


@dataclass(frozen=True)
class ChunkData:
    start_seconds: float
    end_seconds: float
    text: str


def build_chunks(segments: list[TranscriptSegment], max_characters: int = 900) -> list[ChunkData]:
    chunks: list[ChunkData] = []
    current: list[TranscriptSegment] = []
    size = 0
    for segment in segments:
        rendered = f"{segment.speaker.value}: {segment.text}"
        if current and size + len(rendered) > max_characters:
            chunks.append(_render_chunk(current))
            current = []
            size = 0
        current.append(segment)
        size += len(rendered)
    if current:
        chunks.append(_render_chunk(current))
    return chunks


def _render_chunk(segments: list[TranscriptSegment]) -> ChunkData:
    return ChunkData(
        start_seconds=segments[0].start_seconds,
        end_seconds=segments[-1].end_seconds,
        text="\n".join(f"{segment.speaker.value}: {segment.text}" for segment in segments),
    )


class TranscriptIndexer:
    def __init__(self, embedding_provider: EmbeddingProvider, dimensions: int = 768) -> None:
        self.embedding_provider = embedding_provider
        self.dimensions = dimensions

    async def index(self, call_id: uuid.UUID, session: AsyncSession) -> None:
        segments = list(
            await session.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.call_id == call_id)
                .order_by(TranscriptSegment.start_seconds)
            )
        )
        if not segments:
            return
        chunks = build_chunks(segments)
        embeddings = self.embedding_provider.embed([chunk.text for chunk in chunks])
        if any(len(vector) != self.dimensions for vector in embeddings):
            raise RuntimeError(f"Embedding model must return {self.dimensions} dimensions")

        await session.execute(delete(TranscriptChunk).where(TranscriptChunk.call_id == call_id))
        session.add_all(
            TranscriptChunk(
                organization_id=segments[0].organization_id,
                call_id=call_id,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                text=chunk.text,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        )
        await session.commit()


class RagService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        answer_provider: RagAnswerProvider,
        dimensions: int = 768,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.answer_provider = answer_provider
        self.dimensions = dimensions

    async def ask(
        self,
        question: str,
        organization_id: uuid.UUID,
        session: AsyncSession,
        call_id: uuid.UUID | None = None,
        limit: int = 5,
    ) -> AskResponse:
        vector = self.embedding_provider.embed([question])[0]
        if len(vector) != self.dimensions:
            raise RuntimeError(f"Embedding model must return {self.dimensions} dimensions")

        query = select(TranscriptChunk).where(TranscriptChunk.organization_id == organization_id)
        if call_id is not None:
            query = query.where(TranscriptChunk.call_id == call_id)
        query = query.order_by(TranscriptChunk.embedding.cosine_distance(vector)).limit(limit)
        chunks = list(await session.scalars(query))
        if not chunks:
            return AskResponse(answer="Подходящих фрагментов не найдено.", sources=[])

        sources = [
            RagSource(
                call_id=chunk.call_id,
                start_seconds=chunk.start_seconds,
                end_seconds=chunk.end_seconds,
                text=chunk.text,
            )
            for chunk in chunks
        ]
        answer_context = [
            f"Звонок {source.call_id}, {source.start_seconds:.1f}–{source.end_seconds:.1f} сек:\n{source.text}"
            for source in sources
        ]
        return AskResponse(
            answer=self.answer_provider.answer(question, answer_context),
            sources=sources,
        )
