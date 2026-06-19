"""
Punjab Rozgar Portal - FastAPI Backend
Main application entry point with analytics integration
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import logging
from datetime import datetime
from contextlib import asynccontextmanager

# Core imports
from app.core.config import get_settings
from app.core.database import get_database, create_tables
from app.core.logging import setup_logging

# API route imports
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.users import router as users_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.admin import router as admin_router

# Analytics and middleware
from app.analytics.tracker import AnalyticsTracker
from app.middleware.analytics import AnalyticsMiddleware
from app.middleware.security import SecurityMiddleware

# Load settings
settings = get_settings()

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Punjab Rozgar Portal Backend...")
    
    # Initialize database
    await create_tables()
    logger.info("Database tables created/verified")
    
    # Initialize analytics tracker
    analytics_tracker = AnalyticsTracker()
    app.state.analytics = analytics_tracker
    logger.info("Analytics system initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Punjab Rozgar Portal Backend...")

# Create FastAPI application
app = FastAPI(
    title="Punjab Rozgar Portal API",
    description="Employment portal backend with comprehensive analytics for Punjab government",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Security middleware (add these first)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)
app.add_middleware(SecurityMiddleware)
app.add_middleware(AnalyticsMiddleware)

# Configure CORS LAST so it wraps other middleware and adds headers to all responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"]
)

# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "Punjab Rozgar Portal API"
    }

# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Punjab Rozgar Portal API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
        "analytics": "/api/v1/analytics"
    }

# Analytics event tracking endpoint (high priority)
@app.post("/api/track", tags=["Analytics"])
async def track_event(request: Request):
    """Quick event tracking endpoint for frontend"""
    try:
        data = await request.json()
        tracker = request.app.state.analytics
        
        # Track the event
        event_id = await tracker.track_event(
            event_name=data.get("event"),
            properties=data.get("data", {}),
            user_id=data.get("user_id"),
            session_id=data.get("session_id"),
            request=request
        )
        
        return {"success": True, "event_id": event_id}
    
    except Exception as e:
        logger.error(f"Event tracking error: {e}")
        return {"success": False, "error": "Failed to track event"}

# Include API routers
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix="/api/v1/users",
    tags=["Users"]
)

app.include_router(
    jobs_router,
    prefix="/api/v1/jobs", 
    tags=["Jobs"]
)

app.include_router(
    analytics_router,
    prefix="/api/v1/analytics",
    tags=["Analytics"]
)

app.include_router(
    admin_router,
    prefix="/api/v1/admin",
    tags=["Administration"]
)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler with analytics tracking"""
    
    # Track error events
    if hasattr(request.app.state, 'analytics'):
        await request.app.state.analytics.track_event(
            event_name="api_error",
            properties={
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": str(request.url.path),
                "method": request.method
            },
            request=request
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    # Track critical errors
    if hasattr(request.app.state, 'analytics'):
        await request.app.state.analytics.track_event(
            event_name="system_error",
            properties={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "path": str(request.url.path),
                "method": request.method
            },
            request=request
        )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "message": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )
