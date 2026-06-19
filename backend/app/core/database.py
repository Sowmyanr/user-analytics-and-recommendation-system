"""
Database configuration and connection management
SQLAlchemy setup with analytics-optimized schema
"""

import asyncio
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import logging

from app.core.config import get_settings

# Settings
settings = get_settings()
logger = logging.getLogger(__name__)

# Database metadata and base
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Database engines
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
    
    # Sync engine for SQLite
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
    
    # Async engine for SQLite (using aiosqlite)
    async_database_url = SQLALCHEMY_DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
    async_engine = create_async_engine(
        async_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DEBUG
    )

else:
    # PostgreSQL configuration
    SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
    
    # Sync engine for PostgreSQL
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG
    )
    
    # Async engine for PostgreSQL
    async_database_url = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(
        async_database_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        echo=settings.DEBUG
    )

# Session makers
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# SQLite optimization events
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Optimize SQLite for analytics workload"""
        cursor = dbapi_connection.cursor()
        
        # Performance optimizations
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")  # Temp tables in memory
        cursor.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        
        # Analytics optimizations
        cursor.execute("PRAGMA optimize")  # Query optimization
        
        cursor.close()


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    Used with FastAPI dependency injection
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_database():
    """
    Synchronous database session for migrations and utilities
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


async def create_tables():
    """Create all database tables"""
    try:
        # Import all models to register them
        from app.models.user import User
        from app.models.job import Job, JobApplication
        from app.models.analytics import AnalyticsEvent, PageView, UserSession
        from app.models.admin import AdminUser, SystemLog
        
        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {e}")
        raise


async def drop_tables():
    """Drop all database tables (for testing/reset)"""
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("🗑️ Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to drop database tables: {e}")
        raise


async def reset_database():
    """Reset database (drop and recreate tables)"""
    await drop_tables()
    await create_tables()


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    async def health_check() -> dict:
        """Check database connectivity and performance"""
        try:
            async with AsyncSessionLocal() as session:
                # Test basic connectivity
                result = await session.execute("SELECT 1")
                result.scalar()
                
                # Test analytics table if exists
                try:
                    result = await session.execute(
                        "SELECT COUNT(*) FROM analytics_events LIMIT 1"
                    )
                    event_count = result.scalar()
                except:
                    event_count = 0
                
                return {
                    "status": "healthy",
                    "database_type": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
                    "events_tracked": event_count,
                    "connection": "active"
                }
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection": "failed"
            }
    
    @staticmethod
    async def get_analytics_summary() -> dict:
        """Get analytics database summary"""
        try:
            async with AsyncSessionLocal() as session:
                # Import analytics models
                from app.models.analytics import AnalyticsEvent, PageView, UserSession
                from sqlalchemy import func, select
                
                # Get event counts
                event_count = await session.scalar(
                    select(func.count()).select_from(AnalyticsEvent)
                )
                
                # Get page view counts
                page_view_count = await session.scalar(
                    select(func.count()).select_from(PageView)
                )
                
                # Get active sessions
                session_count = await session.scalar(
                    select(func.count()).select_from(UserSession)
                )
                
                return {
                    "total_events": event_count or 0,
                    "total_page_views": page_view_count or 0,
                    "total_sessions": session_count or 0,
                    "status": "active"
                }
                
        except Exception as e:
            logger.error(f"Analytics summary failed: {e}")
            return {
                "total_events": 0,
                "total_page_views": 0,
                "total_sessions": 0,
                "status": "error",
                "error": str(e)
            }
