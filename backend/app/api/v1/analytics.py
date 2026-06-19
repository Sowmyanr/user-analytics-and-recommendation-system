"""
Analytics API Routes
Comprehensive analytics endpoints for Punjab Rozgar Portal
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import json
import logging

from app.core.database import get_database
from app.analytics.tracker import AnalyticsTracker
from app.models.analytics import (
    AnalyticsEvent, PageView, UserSession, JobInteraction, 
    UserBehaviorMetrics, DailyAnalyticsSummary, RealTimeMetrics, ConversionFunnel
)
from app.models.user import User
from app.models.job import Job

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================================
# Pydantic Models for API Requests/Responses
# ============================================================================

class TrackEventRequest(BaseModel):
    """Event tracking request model"""
    event: str = Field(..., description="Event name")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event properties")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    session_id: Optional[str] = Field(None, description="Session ID")
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")

class PageViewRequest(BaseModel):
    """Page view tracking request"""
    page_path: str = Field(..., description="Page path")
    page_title: Optional[str] = Field(None, description="Page title")
    referrer: Optional[str] = Field(None, description="Referrer URL")
    load_time: Optional[float] = Field(None, description="Page load time in seconds")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    session_id: Optional[str] = Field(None, description="Session ID")

class UserActionRequest(BaseModel):
    """User action tracking request"""
    action: str = Field(..., description="Action type (click, search, apply)")
    target: str = Field(..., description="Target element/page")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Action metadata")
    user_id: Optional[str] = Field(None, description="User ID if authenticated")
    session_id: Optional[str] = Field(None, description="Session ID")

class AnalyticsResponse(BaseModel):
    """Standard analytics response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = None

class MetricsResponse(BaseModel):
    """Metrics response model"""
    timestamp: datetime
    metrics: Dict[str, Any]
    period: str
    filters: Optional[Dict[str, Any]] = None

# ============================================================================
# Event Tracking Endpoints
# ============================================================================

@router.post("/track", response_model=AnalyticsResponse)
async def track_event(
    event_data: TrackEventRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_database)
):
    """
    Track any analytics event
    High-performance endpoint for real-time tracking
    """
    try:
        # Get analytics tracker from app state
        tracker: AnalyticsTracker = request.app.state.analytics
        
        # Track the event
        event_id = await tracker.track_event(
            event_name=event_data.event,
            properties=event_data.properties,
            user_id=event_data.user_id,
            session_id=event_data.session_id,
            request=request
        )
        
        # Background task for additional processing
        background_tasks.add_task(
            process_event_background,
            event_data.event,
            event_data.properties,
            event_data.user_id
        )
        
        return AnalyticsResponse(
            success=True,
            message="Event tracked successfully",
            event_id=event_id
        )
        
    except Exception as e:
        logger.error(f"Event tracking failed: {e}")
        return AnalyticsResponse(
            success=False,
            message="Failed to track event"
        )

@router.post("/track/pageview", response_model=AnalyticsResponse)
async def track_page_view(
    page_data: PageViewRequest,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Track page view events"""
    try:
        tracker: AnalyticsTracker = request.app.state.analytics
        
        # Add page-specific properties
        properties = {
            "page_path": page_data.page_path,
            "page_title": page_data.page_title,
            "load_time": page_data.load_time,
            "referrer": page_data.referrer
        }
        
        event_id = await tracker.track_page_view(
            page_path=page_data.page_path,
            user_id=page_data.user_id,
            session_id=page_data.session_id,
            properties=properties,
            request=request
        )
        
        return AnalyticsResponse(
            success=True,
            message="Page view tracked",
            event_id=event_id
        )
        
    except Exception as e:
        logger.error(f"Page view tracking failed: {e}")
        return AnalyticsResponse(
            success=False,
            message="Failed to track page view"
        )

@router.post("/track/action", response_model=AnalyticsResponse)
async def track_user_action(
    action_data: UserActionRequest,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Track user interaction events"""
    try:
        tracker: AnalyticsTracker = request.app.state.analytics
        
        event_id = await tracker.track_user_action(
            action=action_data.action,
            target=action_data.target,
            user_id=action_data.user_id,
            session_id=action_data.session_id,
            metadata=action_data.metadata,
            request=request
        )
        
        return AnalyticsResponse(
            success=True,
            message="User action tracked",
            event_id=event_id
        )
        
    except Exception as e:
        logger.error(f"User action tracking failed: {e}")
        return AnalyticsResponse(
            success=False,
            message="Failed to track user action"
        )

# ============================================================================
# Real-time Analytics Dashboard
# ============================================================================

@router.get("/dashboard/realtime", response_model=MetricsResponse)
async def get_realtime_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Get real-time dashboard metrics"""
    try:
        tracker: AnalyticsTracker = request.app.state.analytics
        metrics = await tracker.get_real_time_metrics()
        
        return MetricsResponse(
            timestamp=datetime.utcnow(),
            metrics=metrics,
            period="realtime"
        )
        
    except Exception as e:
        logger.error(f"Real-time dashboard failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get real-time metrics")

@router.get("/dashboard/overview")
async def get_dashboard_overview(
    period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d"),
    db: AsyncSession = Depends(get_database)
):
    """Get dashboard overview metrics"""
    try:
        # Calculate time range
        now = datetime.utcnow()
        if period == "1h":
            start_time = now - timedelta(hours=1)
        elif period == "24h":
            start_time = now - timedelta(days=1)
        elif period == "7d":
            start_time = now - timedelta(days=7)
        elif period == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        # Get metrics
        metrics = await get_period_metrics(db, start_time, now)
        
        return {
            "success": True,
            "period": period,
            "start_time": start_time.isoformat(),
            "end_time": now.isoformat(),
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Dashboard overview failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard overview")

@router.get("/dashboard/users")
async def get_user_analytics(
    period: str = Query("7d", description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """Get user analytics metrics"""
    try:
        now = datetime.utcnow()
        days = int(period.replace('d', '')) if 'd' in period else 7
        start_time = now - timedelta(days=days)
        
        # User registration trends
        new_users = await db.execute(
            select(func.count(), func.date(User.created_at).label('date'))
            .where(User.created_at >= start_time)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
        )
        
        # Active users (users with recent page views)
        active_users = await db.execute(
            select(func.count(func.distinct(PageView.user_id)))
            .where(
                and_(
                    PageView.timestamp >= start_time,
                    PageView.user_id.isnot(None)
                )
            )
        )
        
        # User behavior metrics
        top_pages = await db.execute(
            select(PageView.page_path, func.count().label('views'))
            .where(PageView.timestamp >= start_time)
            .group_by(PageView.page_path)
            .order_by(desc('views'))
            .limit(10)
        )
        
        return {
            "success": True,
            "period": period,
            "data": {
                "new_users_trend": [
                    {"date": row.date.isoformat(), "count": row[0]}
                    for row in new_users
                ],
                "active_users": active_users.scalar() or 0,
                "top_pages": [
                    {"page": row.page_path, "views": row.views}
                    for row in top_pages
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"User analytics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user analytics")

@router.get("/dashboard/jobs")
async def get_job_analytics(
    period: str = Query("7d", description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """Get job-related analytics"""
    try:
        now = datetime.utcnow()
        days = int(period.replace('d', '')) if 'd' in period else 7
        start_time = now - timedelta(days=days)
        
        # Job posting trends
        new_jobs = await db.execute(
            select(func.count(), func.date(Job.created_at).label('date'))
            .where(Job.created_at >= start_time)
            .group_by(func.date(Job.created_at))
            .order_by(func.date(Job.created_at))
        )
        
        # Job interactions
        job_interactions = await db.execute(
            select(
                JobInteraction.interaction_type,
                func.count().label('count')
            )
            .where(JobInteraction.timestamp >= start_time)
            .group_by(JobInteraction.interaction_type)
        )
        
        # Popular job categories
        popular_categories = await db.execute(
            select(Job.category, func.count().label('jobs'))
            .where(Job.created_at >= start_time)
            .group_by(Job.category)
            .order_by(desc('jobs'))
            .limit(10)
        )
        
        # Application conversion funnel
        funnel_data = await db.execute(
            select(
                ConversionFunnel.step_name,
                func.count().label('count')
            )
            .where(
                and_(
                    ConversionFunnel.timestamp >= start_time,
                    ConversionFunnel.funnel_name == 'job_application'
                )
            )
            .group_by(ConversionFunnel.step_name)
            .order_by(ConversionFunnel.step_name)
        )
        
        return {
            "success": True,
            "period": period,
            "data": {
                "new_jobs_trend": [
                    {"date": row.date.isoformat(), "count": row[0]}
                    for row in new_jobs
                ],
                "job_interactions": [
                    {"type": row.interaction_type, "count": row.count}
                    for row in job_interactions
                ],
                "popular_categories": [
                    {"category": row.category, "jobs": row.jobs}
                    for row in popular_categories
                ],
                "application_funnel": [
                    {"step": row.step_name, "count": row.count}
                    for row in funnel_data
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Job analytics failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job analytics")

# ============================================================================
# Detailed Reports
# ============================================================================

@router.get("/reports/user-behavior/{user_id}")
async def get_user_behavior_report(
    user_id: str,
    days: int = Query(30, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed user behavior report"""
    try:
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # User's events
        events = await db.execute(
            select(AnalyticsEvent)
            .where(
                and_(
                    AnalyticsEvent.user_id == user_id,
                    AnalyticsEvent.timestamp >= start_time
                )
            )
            .order_by(desc(AnalyticsEvent.timestamp))
            .limit(1000)
        )
        
        # User's sessions
        sessions = await db.execute(
            select(UserSession)
            .where(
                and_(
                    UserSession.user_id == user_id,
                    UserSession.started_at >= start_time
                )
            )
            .order_by(desc(UserSession.started_at))
        )
        
        # User's job interactions
        job_interactions = await db.execute(
            select(JobInteraction)
            .where(
                and_(
                    JobInteraction.user_id == user_id,
                    JobInteraction.timestamp >= start_time
                )
            )
            .order_by(desc(JobInteraction.timestamp))
        )
        
        return {
            "success": True,
            "user_id": user_id,
            "period_days": days,
            "data": {
                "events": [event.to_dict() for event in events.scalars()],
                "sessions": [
                    {
                        "session_id": session.session_id,
                        "started_at": session.started_at.isoformat(),
                        "duration": session.duration,
                        "page_views": session.page_views,
                        "events_count": session.events_count
                    }
                    for session in sessions.scalars()
                ],
                "job_interactions": [
                    {
                        "interaction_type": interaction.interaction_type,
                        "job_id": interaction.job_id,
                        "job_title": interaction.job_title,
                        "timestamp": interaction.timestamp.isoformat()
                    }
                    for interaction in job_interactions.scalars()
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"User behavior report failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate user behavior report")

@router.get("/reports/conversion-funnel")
async def get_conversion_funnel_report(
    funnel_name: str = Query("job_application", description="Funnel name"),
    period: str = Query("30d", description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """Get conversion funnel analysis"""
    try:
        days = int(period.replace('d', '')) if 'd' in period else 30
        start_time = datetime.utcnow() - timedelta(days=days)
        
        # Funnel steps with conversion rates
        funnel_steps = await db.execute(
            select(
                ConversionFunnel.step_name,
                ConversionFunnel.step_order,
                func.count().label('users'),
                func.count(ConversionFunnel.completed.is_(True)).label('completed')
            )
            .where(
                and_(
                    ConversionFunnel.funnel_name == funnel_name,
                    ConversionFunnel.timestamp >= start_time
                )
            )
            .group_by(ConversionFunnel.step_name, ConversionFunnel.step_order)
            .order_by(ConversionFunnel.step_order)
        )
        
        # Calculate conversion rates
        funnel_data = []
        previous_users = None
        
        for step in funnel_steps:
            users = step.users
            conversion_rate = 0.0
            
            if previous_users is not None and previous_users > 0:
                conversion_rate = (users / previous_users) * 100
            elif previous_users is None:
                conversion_rate = 100.0  # First step
            
            funnel_data.append({
                "step": step.step_name,
                "order": step.step_order,
                "users": users,
                "completed": step.completed,
                "conversion_rate": round(conversion_rate, 2),
                "completion_rate": round((step.completed / users) * 100, 2) if users > 0 else 0
            })
            
            previous_users = users
        
        return {
            "success": True,
            "funnel_name": funnel_name,
            "period": period,
            "data": {
                "steps": funnel_data,
                "overall_conversion": round(
                    (funnel_data[-1]["users"] / funnel_data[0]["users"]) * 100, 2
                ) if funnel_data and funnel_data[0]["users"] > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Conversion funnel report failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate conversion funnel report")

# ============================================================================
# Administrative Analytics
# ============================================================================

@router.get("/admin/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_database)
):
    """Get administrative statistics"""
    try:
        # Total counts
        total_users = await db.scalar(select(func.count()).select_from(User))
        total_jobs = await db.scalar(select(func.count()).select_from(Job))
        total_events = await db.scalar(select(func.count()).select_from(AnalyticsEvent))
        total_sessions = await db.scalar(select(func.count()).select_from(UserSession))
        
        # Recent activity (last 24 hours)
        day_ago = datetime.utcnow() - timedelta(days=1)
        
        recent_users = await db.scalar(
            select(func.count()).select_from(User)
            .where(User.created_at >= day_ago)
        )
        
        recent_events = await db.scalar(
            select(func.count()).select_from(AnalyticsEvent)
            .where(AnalyticsEvent.timestamp >= day_ago)
        )
        
        recent_page_views = await db.scalar(
            select(func.count()).select_from(PageView)
            .where(PageView.timestamp >= day_ago)
        )
        
        # Active sessions (last hour)
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        active_sessions = await db.scalar(
            select(func.count()).select_from(UserSession)
            .where(UserSession.last_activity >= hour_ago)
        )
        
        return {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "totals": {
                "users": total_users or 0,
                "jobs": total_jobs or 0,
                "events": total_events or 0,
                "sessions": total_sessions or 0
            },
            "recent_24h": {
                "new_users": recent_users or 0,
                "events": recent_events or 0,
                "page_views": recent_page_views or 0
            },
            "current": {
                "active_sessions": active_sessions or 0
            }
        }
        
    except Exception as e:
        logger.error(f"Admin stats failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get admin statistics")

# ============================================================================
# Helper Functions
# ============================================================================

async def get_period_metrics(db: AsyncSession, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
    """Get metrics for a specific time period"""
    
    # Page views
    page_views = await db.scalar(
        select(func.count()).select_from(PageView)
        .where(PageView.timestamp.between(start_time, end_time))
    )
    
    # Unique visitors
    unique_visitors = await db.scalar(
        select(func.count(func.distinct(PageView.session_id)))
        .where(PageView.timestamp.between(start_time, end_time))
    )
    
    # Events
    total_events = await db.scalar(
        select(func.count()).select_from(AnalyticsEvent)
        .where(AnalyticsEvent.timestamp.between(start_time, end_time))
    )
    
    # Job interactions
    job_views = await db.scalar(
        select(func.count()).select_from(JobInteraction)
        .where(
            and_(
                JobInteraction.timestamp.between(start_time, end_time),
                JobInteraction.interaction_type == 'view'
            )
        )
    )
    
    job_applications = await db.scalar(
        select(func.count()).select_from(JobInteraction)
        .where(
            and_(
                JobInteraction.timestamp.between(start_time, end_time),
                JobInteraction.interaction_type == 'apply'
            )
        )
    )
    
    return {
        "page_views": page_views or 0,
        "unique_visitors": unique_visitors or 0,
        "total_events": total_events or 0,
        "job_views": job_views or 0,
        "job_applications": job_applications or 0,
        "conversion_rate": round(
            (job_applications / job_views) * 100, 2
        ) if job_views and job_views > 0 else 0
    }

async def process_event_background(event_name: str, properties: Dict[str, Any], user_id: Optional[str]):
    """Background processing for events"""
    try:
        # Add any background processing logic here
        # For example: updating user behavior metrics, triggering alerts, etc.
        logger.debug(f"Background processing for event: {event_name}")
        
    except Exception as e:
        logger.error(f"Background event processing failed: {e}")
