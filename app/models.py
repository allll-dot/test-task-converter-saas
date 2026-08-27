import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CallStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    calls: Mapped[list["Call"]] = relationship(back_populates="organization")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    audio_path: Mapped[str] = mapped_column(String(1000))
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, native_enum=False), default=CallStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    organization: Mapped[Organization] = relationship(back_populates="calls")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )
    metrics: Mapped["CallMetrics | None"] = relationship(
        back_populates="call", cascade="all, delete-orphan", uselist=False
    )
    analysis: Mapped["CallAnalysis | None"] = relationship(
        back_populates="call", cascade="all, delete-orphan", uselist=False
    )


class Speaker(str, enum.Enum):
    MANAGER = "manager"
    CUSTOMER = "customer"
    UNKNOWN = "unknown"


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.id"), index=True)
    speaker: Mapped[Speaker] = mapped_column(
        Enum(Speaker, native_enum=False), default=Speaker.UNKNOWN
    )
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)

    call: Mapped[Call] = relationship(back_populates="transcript_segments")


class CallMetrics(Base):
    __tablename__ = "call_metrics"

    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.id"), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(index=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    manager_speech_seconds: Mapped[float] = mapped_column(Float)
    customer_speech_seconds: Mapped[float] = mapped_column(Float)
    unknown_speech_seconds: Mapped[float] = mapped_column(Float)
    manager_talk_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_segments: Mapped[int] = mapped_column(Integer)

    call: Mapped[Call] = relationship(back_populates="metrics")


class CallAnalysis(Base):
    __tablename__ = "call_analyses"

    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.id"), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(index=True)
    summary: Mapped[str] = mapped_column(Text)
    topic: Mapped[str] = mapped_column(String(300))
    result: Mapped[str] = mapped_column(String(50))
    sentiment: Mapped[str] = mapped_column(String(50))
    objections: Mapped[list[str]] = mapped_column(JSON)
    agreements: Mapped[list[str]] = mapped_column(JSON)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[int] = mapped_column(Integer)
    model_name: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(50))

    call: Mapped[Call] = relationship(back_populates="analysis")
