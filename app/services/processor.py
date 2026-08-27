import uuid
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Call, CallAnalysis, CallMetrics, CallStatus, TranscriptSegment
from app.services.contracts import AnalysisProvider, TranscriptionProvider
from app.services.metrics import MetricsCalculator


class CallProcessor:
    prompt_version = "call-analysis-v1"

    def __init__(
        self,
        transcription: TranscriptionProvider,
        analysis: AnalysisProvider,
        metrics: MetricsCalculator | None = None,
    ) -> None:
        self.transcription = transcription
        self.analysis = analysis
        self.metrics = metrics or MetricsCalculator()

    async def process(self, call_id: uuid.UUID, session: AsyncSession) -> None:
        call = await session.get(Call, call_id)
        if call is None:
            raise LookupError(f"Call {call_id} not found")

        call.status = CallStatus.PROCESSING
        call.error_message = None
        await session.commit()

        try:
            transcript = self.transcription.transcribe(Path(call.audio_path))
            metrics = self.metrics.calculate(transcript)
            analysis = self.analysis.analyze(transcript)

            # Reprocessing replaces derived data instead of duplicating it.
            await session.execute(
                delete(TranscriptSegment).where(TranscriptSegment.call_id == call.id)
            )
            await session.execute(delete(CallMetrics).where(CallMetrics.call_id == call.id))
            await session.execute(delete(CallAnalysis).where(CallAnalysis.call_id == call.id))

            session.add_all(
                [
                    TranscriptSegment(
                        organization_id=call.organization_id,
                        call_id=call.id,
                        **segment.model_dump(),
                    )
                    for segment in transcript.segments
                ]
            )
            session.add(
                CallMetrics(
                    organization_id=call.organization_id, call_id=call.id, **metrics.model_dump()
                )
            )
            session.add(
                CallAnalysis(
                    organization_id=call.organization_id,
                    call_id=call.id,
                    model_name=self.analysis.model_name,
                    prompt_version=self.prompt_version,
                    **analysis.model_dump(),
                )
            )
            call.status = CallStatus.COMPLETED
            await session.commit()
        except Exception as exc:
            await session.rollback()
            call = await session.get(Call, call_id)
            if call is not None:
                call.status = CallStatus.FAILED
                call.error_message = str(exc)[:1000]
                await session.commit()
            raise
