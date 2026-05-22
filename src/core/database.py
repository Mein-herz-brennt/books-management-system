from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
)

SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e