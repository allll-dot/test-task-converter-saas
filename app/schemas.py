import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import CallStatus, Speaker


class HealthResponse(BaseModel):
    status: str


class CallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    original_filename: str
    status: CallStatus
    error_message: str | None
    created_at: datetime


class TranscriptSegmentData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    speaker: Speaker = Speaker.UNKNOWN
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def end_must_follow_start(self) -> "TranscriptSegmentData":
        if self.end_seconds <= self.start_seconds:
            raise ValueError("end_seconds must be greater than start_seconds")
        return self


class TranscriptData(BaseModel):
    language: str | None = None
    segments: list[TranscriptSegmentData]


class CallMetricsData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    duration_seconds: float
    manager_speech_seconds: float
    customer_speech_seconds: float
    unknown_speech_seconds: float
    manager_talk_ratio: float | None
    total_segments: int


class CallAnalysisData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    result: Literal["resolved", "sale", "callback_scheduled", "rejected", "unknown"]
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    objections: list[str]
    agreements: list[str]
    next_action: str | None
    quality_score: int = Field(ge=0, le=100)


class CallDetailResponse(CallResponse):
    transcript: list[TranscriptSegmentData]
    metrics: CallMetricsData | None
    analysis: CallAnalysisData | None
