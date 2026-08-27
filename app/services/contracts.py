from pathlib import Path
from typing import Protocol

from app.schemas import CallAnalysisData, TranscriptData


class TranscriptionProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    def transcribe(self, audio_path: Path) -> TranscriptData: ...


class AnalysisProvider(Protocol):
    @property
    def model_name(self) -> str: ...

    def analyze(self, transcript: TranscriptData) -> CallAnalysisData: ...
