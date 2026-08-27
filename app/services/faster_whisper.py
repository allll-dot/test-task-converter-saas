from pathlib import Path
from typing import Any

from app.models import Speaker
from app.schemas import TranscriptData, TranscriptSegmentData


class FasterWhisperProvider:
    """Free local speech recognition adapter.

    Whisper produces timestamped segments but does not identify call roles, so
    speakers intentionally remain UNKNOWN until a diarization/channel adapter
    resolves them.
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model: Any | None = None

    @property
    def model_name(self) -> str:
        return f"faster-whisper:{self._model_size}"

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "Install the local AI dependencies with: pip install -e '.[local-ai]'"
                ) from exc
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    def transcribe(self, audio_path: Path) -> TranscriptData:
        segments, info = self._load_model().transcribe(
            str(audio_path),
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        result = [
            TranscriptSegmentData(
                speaker=Speaker.UNKNOWN,
                start_seconds=segment.start,
                end_seconds=segment.end,
                text=segment.text.strip(),
            )
            for segment in segments
            if segment.text.strip() and segment.end > segment.start
        ]
        return TranscriptData(language=info.language, segments=result)
