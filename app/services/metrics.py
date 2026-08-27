from app.models import Speaker
from app.schemas import CallMetricsData, TranscriptData


class MetricsCalculator:
    def calculate(self, transcript: TranscriptData) -> CallMetricsData:
        durations = {speaker: 0.0 for speaker in Speaker}
        for segment in transcript.segments:
            durations[segment.speaker] += segment.end_seconds - segment.start_seconds

        known_speech = durations[Speaker.MANAGER] + durations[Speaker.CUSTOMER]
        manager_ratio = durations[Speaker.MANAGER] / known_speech if known_speech else None
        duration = max((segment.end_seconds for segment in transcript.segments), default=0.0)

        return CallMetricsData(
            duration_seconds=round(duration, 3),
            manager_speech_seconds=round(durations[Speaker.MANAGER], 3),
            customer_speech_seconds=round(durations[Speaker.CUSTOMER], 3),
            unknown_speech_seconds=round(durations[Speaker.UNKNOWN], 3),
            manager_talk_ratio=round(manager_ratio, 4) if manager_ratio is not None else None,
            total_segments=len(transcript.segments),
        )
