"""
Analytics Tracker - Core analytics engine for Punjab Rozgar Portal
Handles event tracking, user behavior analysis, and real-time metrics
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AnalyticsEvent:
    """Analytics event data structure"""
    event_name: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    properties: Dict[str, Any] = None
    page_url: Optional[str] = None
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.properties is None:
            self.properties = {}


class AnalyticsTracker:
    """
    Main analytics tracking engine
    Handles real-time event collection and processing
    """
    
    def __init__(self):
        self.event_queue: List[AnalyticsEvent] = []
        self.session_cache: Dict[str, Dict] = {}
        self.metrics_cache: Dict[str, Any] = {}
        self.last_flush = datetime.utcnow()
        self._bg_started = False
        
        # Start background processing
        if settings.ANALYTICS_ENABLED:
            self._ensure_background_task()

    def _ensure_background_task(self):
        """Start background processor if event loop is running; otherwise, defer."""
        if self._bg_started or not settings.ANALYTICS_ENABLED:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._background_processor())
            self._bg_started = True
            logger.debug("Analytics background processor started")
        except RuntimeError:
            # No running event loop; will try again on next call
            logger.debug("No running event loop; deferring analytics background start")
    
    async def track_event(
        self, 
        event_name: str,
        properties: Dict[str, Any] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request: Optional[Request] = None
    ) -> str:
        """
        Track an analytics event
        
        Args:
            event_name: Name of the event (e.g., 'job_search', 'application_submit')
            properties: Event properties and metadata
            user_id: Authenticated user ID
            session_id: Browser session ID
            request: FastAPI request object for extracting metadata
        
        Returns:
            Event ID for tracking
        """
        if not settings.ANALYTICS_ENABLED:
            return "analytics_disabled"
        
        try:
            # Ensure background task is started if possible
            self._ensure_background_task()
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Extract request metadata
            page_url = None
            referrer = None
            user_agent = None
            ip_address = None
            
            if request:
                page_url = str(request.url)
                referrer = request.headers.get("referer")
                user_agent = request.headers.get("user-agent")
                ip_address = self._get_client_ip(request)
                
                # Auto-generate session ID if not provided
                if not session_id:
                    session_id = self._extract_session_id(request)
            
            # Create event
            event = AnalyticsEvent(
                event_name=event_name,
                user_id=user_id,
                session_id=session_id,
                properties=properties or {},
                page_url=page_url,
                referrer=referrer,
                user_agent=user_agent,
                ip_address=ip_address
            )
            
            # Add event ID to properties
            event.properties["event_id"] = event_id
            
            # Queue for processing
            self.event_queue.append(event)
            
            # Update session cache
            if session_id:
                await self._update_session_cache(session_id, event)
            
            # Immediate flush if queue is full
            if len(self.event_queue) >= settings.ANALYTICS_BATCH_SIZE:
                await self._flush_events()
            
            logger.debug(f"Tracked event: {event_name} for user: {user_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to track event {event_name}: {e}")
            return "error"
    
    async def track_page_view(
        self,
        page_path: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        properties: Dict[str, Any] = None,
        request: Optional[Request] = None
    ) -> str:
        """Track a page view event"""
        
        page_properties = {
            "page_path": page_path,
            "page_type": self._classify_page(page_path),
            **(properties or {})
        }
        
        return await self.track_event(
            event_name="page_view",
            properties=page_properties,
            user_id=user_id,
            session_id=session_id,
            request=request
        )
    
    async def track_user_action(
        self,
        action: str,
        target: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        request: Optional[Request] = None
    ) -> str:
        """Track user interaction events"""
        
        action_properties = {
            "action": action,
            "target": target,
            "category": "user_interaction",
            **(metadata or {})
        }
        
        return await self.track_event(
            event_name="user_action",
            properties=action_properties,
            user_id=user_id,
            session_id=session_id,
            request=request
        )
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time analytics metrics"""
        try:
            async with AsyncSessionLocal() as session:
                # Import models
                from app.models.analytics import AnalyticsEvent as DBEvent, PageView, UserSession
                
                now = datetime.utcnow()
                hour_ago = now - timedelta(hours=1)
                day_ago = now - timedelta(days=1)
                
                # Events in last hour
                events_hour = await session.scalar(
                    select(func.count()).select_from(DBEvent)
                    .where(DBEvent.timestamp >= hour_ago)
                )
                
                # Page views today
                page_views_today = await session.scalar(
                    select(func.count()).select_from(PageView)
                    .where(PageView.timestamp >= day_ago)
                )
                
                # Active sessions
                active_sessions = await session.scalar(
                    select(func.count()).select_from(UserSession)
                    .where(
                        and_(
                            UserSession.last_activity >= hour_ago,
                            UserSession.ended_at.is_(None)
                        )
                    )
                )
                
                # Popular pages (last 24h)
                popular_pages = await session.execute(
                    select(PageView.page_path, func.count().label('views'))
                    .where(PageView.timestamp >= day_ago)
                    .group_by(PageView.page_path)
                    .order_by(func.count().desc())
                    .limit(10)
                )
                
                return {
                    "timestamp": now.isoformat(),
                    "events_last_hour": events_hour or 0,
                    "page_views_today": page_views_today or 0,
                    "active_sessions": active_sessions or 0,
                    "popular_pages": [
                        {"page": row.page_path, "views": row.views}
                        for row in popular_pages
                    ],
                    "queue_size": len(self.event_queue)
                }
                
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "events_last_hour": 0,
                "page_views_today": 0,
                "active_sessions": 0,
                "popular_pages": [],
                "error": str(e)
            }
    
    async def get_user_journey(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user journey events"""
        try:
            async with AsyncSessionLocal() as session:
                from app.models.analytics import AnalyticsEvent as DBEvent
                
                events = await session.execute(
                    select(DBEvent)
                    .where(DBEvent.user_id == user_id)
                    .order_by(DBEvent.timestamp.desc())
                    .limit(100)
                )
                
                return [
                    {
                        "event_name": event.event_name,
                        "timestamp": event.timestamp.isoformat(),
                        "properties": event.properties,
                        "page_url": event.page_url
                    }
                    for event in events
                ]
                
        except Exception as e:
            logger.error(f"Failed to get user journey for {user_id}: {e}")
            return []
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded IP (load balancers, proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _extract_session_id(self, request: Request) -> str:
        """Extract or generate session ID"""
        # Try to get from cookie
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # Try to get from headers
        session_id = request.headers.get("x-session-id")
        if session_id:
            return session_id
        
        # Generate new session ID
        return f"session_{uuid.uuid4().hex[:16]}"
    
    def _classify_page(self, page_path: str) -> str:
        """Classify page type for analytics"""
        if "/jobs" in page_path:
            return "jobs"
        elif "/profile" in page_path:
            return "profile"
        elif "/admin" in page_path:
            return "admin"
        elif "/auth" in page_path:
            return "authentication"
        elif "/analytics" in page_path:
            return "analytics"
        else:
            return "general"
    
    async def _update_session_cache(self, session_id: str, event: AnalyticsEvent):
        """Update session information in cache"""
        if session_id not in self.session_cache:
            self.session_cache[session_id] = {
                "session_id": session_id,
                "first_seen": event.timestamp,
                "last_seen": event.timestamp,
                "page_views": 0,
                "events": 0,
                "pages_visited": set()
            }
        
        cache = self.session_cache[session_id]
        cache["last_seen"] = event.timestamp
        cache["events"] += 1
        
        if event.event_name == "page_view":
            cache["page_views"] += 1
            if event.page_url:
                cache["pages_visited"].add(event.page_url)
    
    async def _flush_events(self):
        """Flush queued events to database"""
        if not self.event_queue:
            return
        
        try:
            async with AsyncSessionLocal() as session:
                from app.models.analytics import AnalyticsEvent as DBEvent, PageView, UserSession
                
                # Process events
                db_events = []
                page_views = []
                sessions_to_update = {}
                
                for event in self.event_queue:
                    # Create analytics event record
                    db_event = DBEvent(
                        event_name=event.event_name,
                        user_id=event.user_id,
                        session_id=event.session_id,
                        timestamp=event.timestamp,
                        properties=event.properties,
                        page_url=event.page_url,
                        referrer=event.referrer,
                        user_agent=event.user_agent,
                        ip_address=event.ip_address
                    )
                    db_events.append(db_event)
                    
                    # Create page view record if applicable
                    if event.event_name == "page_view" and event.page_url:
                        page_view = PageView(
                            session_id=event.session_id,
                            user_id=event.user_id,
                            page_path=event.properties.get("page_path", event.page_url),
                            page_title=event.properties.get("page_title"),
                            timestamp=event.timestamp,
                            load_time=event.properties.get("load_time"),
                            referrer=event.referrer
                        )
                        page_views.append(page_view)
                    
                    # Track sessions
                    if event.session_id and event.session_id in self.session_cache:
                        sessions_to_update[event.session_id] = self.session_cache[event.session_id]
                
                # Bulk insert events
                session.add_all(db_events)
                session.add_all(page_views)
                
                # Update sessions
                for session_id, session_data in sessions_to_update.items():
                    # Convert set to list for JSON serialization
                    session_data["pages_visited"] = list(session_data["pages_visited"])
                    
                    user_session = UserSession(
                        session_id=session_id,
                        user_id=session_data.get("user_id"),
                        started_at=session_data["first_seen"],
                        last_activity=session_data["last_seen"],
                        page_views=session_data["page_views"],
                        events_count=session_data["events"],
                        pages_visited=session_data["pages_visited"]
                    )
                    
                    # Upsert session (update if exists)
                    await session.merge(user_session)
                
                await session.commit()
                
                logger.info(f"Flushed {len(db_events)} events to database")
                
                # Clear queue and update last flush time
                self.event_queue.clear()
                self.last_flush = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Failed to flush events to database: {e}")
    
    async def _background_processor(self):
        """Background task to periodically flush events"""
        while settings.ANALYTICS_ENABLED:
            try:
                await asyncio.sleep(settings.ANALYTICS_FLUSH_INTERVAL)
                
                # Check if it's time to flush
                if (datetime.utcnow() - self.last_flush).seconds >= settings.ANALYTICS_FLUSH_INTERVAL:
                    await self._flush_events()
                
                # Clean old session cache
                await self._cleanup_session_cache()
                
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _cleanup_session_cache(self):
        """Clean up old sessions from cache"""
        cutoff = datetime.utcnow() - timedelta(hours=24)
        
        sessions_to_remove = [
            session_id for session_id, data in self.session_cache.items()
            if data["last_seen"] < cutoff
        ]
        
        for session_id in sessions_to_remove:
            del self.session_cache[session_id]
        
        if sessions_to_remove:
            logger.debug(f"Cleaned up {len(sessions_to_remove)} old sessions from cache")


# Global analytics tracker instance
_analytics_tracker = None

def get_analytics_tracker() -> AnalyticsTracker:
    """Get the global analytics tracker instance"""
    global _analytics_tracker
    if _analytics_tracker is None:
        _analytics_tracker = AnalyticsTracker()
    return _analytics_tracker
