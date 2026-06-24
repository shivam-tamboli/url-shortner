import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import app.database as db_module
import app.routers.urls as urls_module
from app.config import settings
from main import app


@pytest.fixture(autouse=True)
async def isolate_db():
    # NullPool gives each request its own connection so background tasks
    # from one request cannot conflict with the next request
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    test_session = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    db_module.AsyncSessionLocal = test_session
    urls_module.AsyncSessionLocal = test_session
    yield
    await test_engine.dispose()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
