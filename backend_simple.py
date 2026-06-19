from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import asyncio

# Create FastAPI instance
app = FastAPI(
    title="Punjab Rozgar Analytics API",
    description="Analytics API for Punjab Rozgar Portal",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for testing
analytics_data = []
user_sessions = {}

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {
        "message": "Punjab Rozgar Analytics API",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "analytics_events": len(analytics_data),
        "active_sessions": len(user_sessions)
    }

# Analytics Endpoints
@app.post("/api/v1/analytics/track")
async def track_event(event_data: dict):
    """Track analytics event"""
    try:
        event = {
            "id": len(analytics_data) + 1,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_data.get("event_type", "pageview"),
            "page_url": event_data.get("page_url"),
            "user_agent": event_data.get("user_agent"),
            "ip_address": event_data.get("ip_address"),
            "session_id": event_data.get("session_id"),
            "user_id": event_data.get("user_id"),
            "properties": event_data.get("properties", {})
        }
        
        analytics_data.append(event)
        
        return {
            "success": True,
            "event_id": event["id"],
            "message": "Event tracked successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error tracking event: {str(e)}")

@app.get("/api/v1/analytics/events")
async def get_events(limit: int = 100):
    """Get recent analytics events"""
    return {
        "events": analytics_data[-limit:],
        "total_events": len(analytics_data),
        "limit": limit
    }

@app.get("/api/v1/analytics/dashboard")
async def get_dashboard_data():
    """Get dashboard analytics data"""
    if not analytics_data:
        return {
            "total_events": 0,
            "page_views": 0,
            "unique_sessions": 0,
            "top_pages": [],
            "hourly_stats": []
        }
    
    # Calculate basic stats
    page_views = len([e for e in analytics_data if e["event_type"] == "pageview"])
    unique_sessions = len(set(e["session_id"] for e in analytics_data if e.get("session_id")))
    
    # Top pages
    page_counts = {}
    for event in analytics_data:
        if event.get("page_url"):
            page_counts[event["page_url"]] = page_counts.get(event["page_url"], 0) + 1
    
    top_pages = sorted(page_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_events": len(analytics_data),
        "page_views": page_views,
        "unique_sessions": unique_sessions,
        "top_pages": [{"url": url, "views": count} for url, count in top_pages],
        "hourly_stats": []  # Simplified for now
    }

# Auth Endpoints (Simplified)
@app.post("/api/v1/auth/register")
async def register(user_data: dict):
    """Simple user registration"""
    return {
        "success": True,
        "message": "User registered successfully",
        "user_id": f"user_{len(analytics_data) + 1}"
    }

@app.post("/api/v1/auth/login")
async def login(credentials: dict):
    """Simple user login"""
    return {
        "success": True,
        "access_token": "dummy_token_123",
        "token_type": "bearer",
        "user": {
            "id": "user_1",
            "email": credentials.get("email", "user@example.com"),
            "role": "job_seeker"
        }
    }

# Jobs Endpoints (Simplified)
@app.get("/api/v1/jobs")
async def get_jobs():
    """Get job listings"""
    return {
        "jobs": [
            {
                "id": 1,
                "title": "Software Developer",
                "company": "Tech Corp",
                "location": "Lahore",
                "salary": "50,000 - 80,000 PKR",
                "posted_date": datetime.now().isoformat()
            },
            {
                "id": 2,
                "title": "Data Analyst",
                "company": "Data Solutions",
                "location": "Karachi",
                "salary": "40,000 - 60,000 PKR",
                "posted_date": datetime.now().isoformat()
            }
        ],
        "total": 2
    }

@app.post("/api/v1/jobs")
async def create_job(job_data: dict):
    """Create new job posting"""
    return {
        "success": True,
        "job_id": f"job_{len(analytics_data) + 1}",
        "message": "Job created successfully"
    }

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "backend_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
