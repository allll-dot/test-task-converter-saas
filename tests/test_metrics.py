import pytest

from app.models import Speaker
from app.schemas import TranscriptData, TranscriptSegmentData
from app.services.metrics import MetricsCalculator


def test_calculates_speaker_durations_and_ratio():
    transcript = TranscriptData(
        language="ru",
        segments=[
            TranscriptSegmentData(
                speaker=Speaker.MANAGER, start_seconds=0, end_seconds=6, text="Здравствуйте"
            ),
            TranscriptSegmentData(
                speaker=Speaker.CUSTOMER, start_seconds=7, end_seconds=11, text="Добрый день"
            ),
            TranscriptSegmentData(
                speaker=Speaker.MANAGER, start_seconds=12, end_seconds=14, text="Слушаю вас"
            ),
        ],
    )

    metrics = MetricsCalculator().calculate(transcript)

    assert metrics.duration_seconds == 14
    assert metrics.manager_speech_seconds == 8
    assert metrics.customer_speech_seconds == 4
    assert metrics.manager_talk_ratio == pytest.approx(0.6667)
    assert metrics.total_segments == 3


def test_ratio_is_unknown_without_resolved_speakers():
    transcript = TranscriptData(
        segments=[
            TranscriptSegmentData(start_seconds=1, end_seconds=3, text="Неизвестный спикер")
        ]
    )

    metrics = MetricsCalculator().calculate(transcript)

    assert metrics.manager_talk_ratio is None
    assert metrics.unknown_speech_seconds == 2
