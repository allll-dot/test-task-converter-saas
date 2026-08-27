import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Call, Organization
from app.schemas import CallDetailResponse, CallResponse, HealthResponse
from app.services.dispatcher import TaskDispatcher, get_task_dispatcher
from app.storage import AudioStorage, InvalidAudioFile

router = APIRouter()


def tenant_id(x_organization_id: Annotated[uuid.UUID, Header()]) -> uuid.UUID:
    return x_organization_id


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/api/v1/calls", response_model=CallResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_call(
    file: Annotated[UploadFile, File()],
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    dispatcher: Annotated[TaskDispatcher, Depends(get_task_dispatcher)],
) -> Call:
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")

    storage = AudioStorage(settings.upload_dir, settings.max_upload_bytes)
    try:
        path = await storage.save_mp3(file, organization_id)
    except InvalidAudioFile as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    call = Call(
        organization_id=organization_id,
        original_filename=file.filename or "call.mp3",
        audio_path=str(path),
    )
    session.add(call)
    await session.commit()
    await session.refresh(call)
    dispatcher.enqueue(call.id)
    return call


@router.get("/api/v1/calls", response_model=list[CallResponse])
async def list_calls(
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Call]:
    result = await session.scalars(
        select(Call).where(Call.organization_id == organization_id).order_by(Call.created_at.desc())
    )
    return list(result)


@router.get("/api/v1/calls/{call_id}", response_model=CallDetailResponse)
async def get_call(
    call_id: uuid.UUID,
    organization_id: Annotated[uuid.UUID, Depends(tenant_id)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    call = await session.scalar(
        select(Call)
        .options(
            selectinload(Call.transcript_segments),
            selectinload(Call.metrics),
            selectinload(Call.analysis),
        )
        .where(Call.id == call_id, Call.organization_id == organization_id)
    )
    if call is None:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "id": call.id,
        "organization_id": call.organization_id,
        "original_filename": call.original_filename,
        "status": call.status,
        "error_message": call.error_message,
        "created_at": call.created_at,
        "transcript": call.transcript_segments,
        "metrics": call.metrics,
        "analysis": call.analysis,
    }
