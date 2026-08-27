import os
from pathlib import Path

os.environ["APP_DATABASE_URL"] = "sqlite+aiosqlite:///./test_calls.db"
os.environ["APP_UPLOAD_DIR"] = "./test_uploads"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, SessionFactory, engine
from app.main import app
from app.models import Organization


@pytest.fixture
def organization_id() -> str:
    import uuid

    return str(uuid.uuid4())


@pytest.fixture
def client(organization_id: str):
    import asyncio
    import uuid

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        async with SessionFactory() as session:
            session.add(Organization(id=uuid.UUID(organization_id), name="Demo company"))
            await session.commit()

    asyncio.run(prepare())
    with TestClient(app) as test_client:
        yield test_client

    for path in Path("test_uploads").glob("**/*.mp3"):
        path.unlink()
