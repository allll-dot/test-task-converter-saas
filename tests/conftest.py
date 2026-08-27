import os
import uuid
from pathlib import Path

os.environ["APP_DATABASE_URL"] = "sqlite+aiosqlite:///./test_calls.db"
os.environ["APP_UPLOAD_DIR"] = "./test_uploads"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionFactory, engine
from app.main import app
from app.models import Organization
from app.services.dispatcher import get_task_dispatcher


class FakeTaskDispatcher:
    def __init__(self) -> None:
        self.enqueued: list[uuid.UUID] = []

    def enqueue(self, call_id: uuid.UUID) -> None:
        self.enqueued.append(call_id)


@pytest.fixture
def organization_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def task_dispatcher() -> FakeTaskDispatcher:
    return FakeTaskDispatcher()


@pytest.fixture
def client(organization_id: str, task_dispatcher: FakeTaskDispatcher):
    import asyncio

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with SessionFactory() as session:
            session.add(Organization(id=uuid.UUID(organization_id), name="Demo company"))
            await session.commit()

    asyncio.run(prepare())
    app.dependency_overrides[get_task_dispatcher] = lambda: task_dispatcher
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()

    for path in Path("test_uploads").glob("**/*.mp3"):
        path.unlink()
