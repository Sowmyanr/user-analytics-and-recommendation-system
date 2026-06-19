"""
Core configuration settings for Punjab Rozgar Portal    # Email settings (optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    SMTP_USER: Optional[str] = None  # Alternative field name
    FROM_EMAIL: Optional[str] = None  # From email address
    
    # Cache settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutesnt-based configuration with analytics settings
"""

import os
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings with analytics configuration"""
    
    # Application settings
    APP_NAME: str = "Punjab Rozgar Portal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Security settings
    SECRET_KEY: str = "punjab-rozgar-portal-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./punjab_rozgar.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Analytics settings
    ANALYTICS_ENABLED: bool = True
    ANALYTICS_BATCH_SIZE: int = 100
    ANALYTICS_FLUSH_INTERVAL: int = 60  # seconds
    ANALYTICS_RETENTION_DAYS: int = 365
    
    # CORS settings
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"]
    UPLOAD_DIR: str = "uploads"
    
    # Email settings (for notifications)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    
    # Cache settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 300  # 5 minutes
    
    # External API settings
    GOVERNMENT_API_KEY: Optional[str] = None
    GOVERNMENT_API_URL: Optional[str] = None
    
    # Feature flags
    ENABLE_REGISTRATION: bool = True
    ENABLE_JOB_POSTING: bool = True
    ENABLE_ANALYTICS_DASHBOARD: bool = True
    ENABLE_ML_RECOMMENDATIONS: bool = False
    
    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v):
        if v.startswith("sqlite"):
            # Ensure directory exists for SQLite
            db_path = v.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        return v
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }


class DevelopmentSettings(Settings):
    """Development environment settings"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_URL: str = "sqlite:///./dev_punjab_rozgar.db"
    
    # More permissive CORS for development
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5500",
        "http://127.0.0.1:5500"
    ]


class ProductionSettings(Settings):
    """Production environment settings"""
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Strict security in production
    ALLOWED_HOSTS: List[str] = ["punjabrozgar.gov.in", "www.punjabrozgar.gov.in"]
    ALLOWED_ORIGINS: List[str] = ["https://punjabrozgar.gov.in"]
    
    # Production database (PostgreSQL recommended)
    DATABASE_URL: str = "postgresql://user:password@localhost/punjab_rozgar"
    
    # Enhanced security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        if not v or len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production")
        return v


class TestingSettings(Settings):
    """Testing environment settings"""
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///:memory:"
    ANALYTICS_ENABLED: bool = False
    LOG_LEVEL: str = "WARNING"


@lru_cache()
def get_settings() -> Settings:
    """Get application settings based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return ProductionSettings()
    elif environment == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Export settings instance
settings = get_settings()
