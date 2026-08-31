from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = None
async_session = None


class Base(DeclarativeBase):
    pass


def init_db():
    global engine, async_session
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db():
    if async_session is None:
        init_db()
    async with async_session() as session:
        yield session
