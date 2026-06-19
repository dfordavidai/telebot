"""Database configuration and session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class Database:
    """Database connection manager."""
    
    def __init__(self):
        settings = get_settings()
        # Convert postgres:// to postgresql:// for SQLAlchemy 2.0+
        db_url = settings.DATABASE_URL.replace("postgres://", "postgresql://")
        
        self.engine = create_engine(
            db_url,
            echo=settings.LOG_LEVEL == "DEBUG",
            pool_pre_ping=True,  # Validate connections
            pool_size=5,
            max_overflow=10
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def init_db(self):
        """Create all tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables initialized")


# Global instance
db = Database()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()
