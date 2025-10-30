"""
Database configuration and connection.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from .config import get_settings

settings = get_settings()

# Create engine if database URL is configured
engine = None
SessionLocal = None

if settings.database_url:
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    """Get database session."""
    if SessionLocal is None:
        # No database configured, return None
        return None

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()