from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(settings.database_url, future=True, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory():
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, class_=Session, future=True)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_db_connection() -> bool:
    if not settings.use_database:
        return False
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False