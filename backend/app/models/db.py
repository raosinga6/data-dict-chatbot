# app/models/db.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

class Base(DeclarativeBase):
    pass

_engine = None
_factory = None

def get_engine():
    global _engine
    if _engine is None:
        s = get_settings()
        _engine = create_async_engine(
            s.database_url,
            echo=(s.environment == "development"),
            pool_pre_ping=True,
        )
    return _engine

def get_session_factory():
    global _factory
    if _factory is None:
        _factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _factory

async def get_db():
    async with get_session_factory()() as session:
        yield session