from app.tasks import process_call


def test_registers_call_processing_task() -> None:
    assert process_call.name == "calls.process"
    assert process_call.max_retries == 3
