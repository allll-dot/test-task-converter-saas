import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas import CallAnalysisData, TranscriptData

SYSTEM_PROMPT = """Ты анализируешь телефонный звонок на русском языке.
Используй только факты из транскрипта. Не придумывай отсутствующие сведения.
Если результат звонка неизвестен, используй unknown. Пустые множества возвращай
как пустые списки. quality_score оценивай от 0 до 100 по ясности коммуникации,
выявлению потребности, работе с возражениями и фиксации следующего шага."""


class OllamaAnalysisProvider:
    """Structured analysis through a locally running, free Ollama model."""

    def __init__(self, base_url: str, model: str, timeout_seconds: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self._model = model
        self.timeout_seconds = timeout_seconds

    @property
    def model_name(self) -> str:
        return f"ollama:{self._model}"

    def analyze(self, transcript: TranscriptData) -> CallAnalysisData:
        transcript_text = "\n".join(
            f"[{part.start_seconds:.2f}-{part.end_seconds:.2f}] {part.speaker.value}: {part.text}"
            for part in transcript.segments
        )
        payload = {
            "model": self._model,
            "stream": False,
            "format": CallAnalysisData.model_json_schema(),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript_text},
            ],
            "options": {"temperature": 0},
        }
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"Local Ollama request failed: {exc}") from exc

        try:
            return CallAnalysisData.model_validate_json(body["message"]["content"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Ollama returned an invalid structured response") from exc
