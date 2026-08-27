import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import tenant_id
from app.config import Settings, get_settings
from app.db import get_session
from app.schemas import AskRequest, AskResponse
from app.services.ollama_rag import OllamaEmbeddingProvider, OllamaRagAnswerProvider
from app.services.rag import RagService

router = APIRouter()


def get_rag_service(settings: Annotated[Settings, Depends(get_settings)]) -> RagService:
    return RagService(
        embedding_provider=OllamaEmbeddingProvider(
            settings.ollama_url, settings.ollama_embedding_model
        ),
        answer_provider=OllamaRagAnswerProvider(settings.ollama_url, settings.ollama_model),
        dimensions=settings.embedding_dimensions,
    )


@router.post("/api/v1/analytics/ask", response_model=AskResponse)
async def ask_calls(
    request: AskRequest,
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    rag_service: Annotated[RagService, Depends(get_rag_service)],
) -> AskResponse:
    try:
        return await rag_service.ask(
            question=request.question,
            organization_id=organization_id,
            session=session,
            call_id=request.call_id,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503, detail="RAG service is temporarily unavailable"
        ) from exc
