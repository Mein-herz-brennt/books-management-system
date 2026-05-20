import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import delete

from src.main import app
from src.core.database import Base, get_db
from src.modules.users.models import User


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    SessionLocal = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False
    )
    
    async with SessionLocal() as session:
        yield session
        # Cleanup users after each test
        await session.execute(delete(User))
        await session.commit()


@pytest.fixture
async def client(db_session):
    # Override get_db dependency to use the test db session
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Create AsyncClient using ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
        
    app.dependency_overrides.clear()


@pytest.fixture
async def create_test_user(db_session):
    from src.core.security import get_password_hash
    
    async def _create(username="testuser", password="testpassword"):
        user = User(
            username=username,
            password=get_password_hash(password)
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
        
    return _create
