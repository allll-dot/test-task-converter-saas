import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Organization


async def seed_demo_organization() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            organization = await session.get(Organization, settings.demo_organization_id)
            if organization is None:
                session.add(
                    Organization(id=settings.demo_organization_id, name="Demo organization")
                )
                await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_organization())
