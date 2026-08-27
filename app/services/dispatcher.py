import uuid
from functools import lru_cache
from typing import Protocol


class TaskDispatcher(Protocol):
    def enqueue(self, call_id: uuid.UUID) -> None: ...


class CeleryTaskDispatcher:
    def enqueue(self, call_id: uuid.UUID) -> None:
        from app.tasks import process_call

        process_call.delay(str(call_id))


@lru_cache
def get_task_dispatcher() -> TaskDispatcher:
    return CeleryTaskDispatcher()
