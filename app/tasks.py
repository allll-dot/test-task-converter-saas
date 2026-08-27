import asyncio
import logging
import uuid

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.celery_app import celery_app
from app.config import get_settings
from app.services.faster_whisper import FasterWhisperProvider
from app.services.ollama import OllamaAnalysisProvider
from app.services.ollama_rag import OllamaEmbeddingProvider
from app.services.processor import CallProcessor
from app.services.rag import TranscriptIndexer

logger = logging.getLogger(__name__)


async def _process_call(call_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, poolclass=pool.NullPool)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    processor = CallProcessor(
        transcription=FasterWhisperProvider(
            model_size=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        ),
        analysis=OllamaAnalysisProvider(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
        ),
    )
    try:
        async with session_factory() as session:
            await processor.process(call_id, session)
            indexer = TranscriptIndexer(
                OllamaEmbeddingProvider(settings.ollama_url, settings.ollama_embedding_model),
                dimensions=settings.embedding_dimensions,
            )
            try:
                await indexer.index(call_id, session)
            except RuntimeError:
                # RAG is optional: embedding downtime must not invalidate call analytics.
                logger.warning("RAG indexing failed for call %s", call_id, exc_info=True)
    finally:
        await engine.dispose()


@celery_app.task(
    name="calls.process",
    autoretry_for=(RuntimeError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def process_call(call_id: str) -> None:
    asyncio.run(_process_call(uuid.UUID(call_id)))
