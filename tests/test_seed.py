import uuid

import pytest
from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionFactory
from app.models import Organization
from app.seed import seed_demo_organization


@pytest.mark.asyncio
async def test_seeds_demo_organization_idempotently(client):
    await seed_demo_organization()
    await seed_demo_organization()

    demo_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    async with SessionFactory() as session:
        organization = await session.get(Organization, demo_id)
        count = await session.scalar(
            select(func.count(Organization.id)).where(Organization.id == demo_id)
        )

    assert organization is not None
    assert organization.name == "Demo organization"
    assert count == 1
    assert get_settings().demo_organization_id == demo_id
