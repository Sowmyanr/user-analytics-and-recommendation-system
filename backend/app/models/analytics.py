"""
Analytics Database Models
Optimized for high-volume event tracking and real-time analytics
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.database import Base


class AnalyticsEvent(Base):
    """
    Core analytics event table
    Stores all user interactions and system events
    """
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(100), nullable=False, index=True)
    user_id = Column(String(50), index=True)  # Can be authenticated user or anonymous
    session_id = Column(String(100), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Event properties (JSON for flexibility)
    properties = Column(JSON, default=dict)
    
    # Request metadata
    page_url = Column(Text)
    referrer = Column(Text)
    user_agent = Column(Text)
    ip_address = Column(String(45))  # IPv6 compatible
    
    # Performance tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes for analytics queries
    __table_args__ = (
        Index('idx_analytics_event_time', 'event_name', 'timestamp'),
        Index('idx_analytics_user_time', 'user_id', 'timestamp'),
        Index('idx_analytics_session_time', 'session_id', 'timestamp'),
        Index('idx_analytics_daily', 'event_name', func.date(timestamp)),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'event_name': self.event_name,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'properties': self.properties,
            'page_url': self.page_url,
            'referrer': self.referrer,
            'ip_address': self.ip_address
        }


class PageView(Base):
    """
    Page view tracking optimized for web analytics
    """
    __tablename__ = "page_views"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(50), index=True)
    
    # Page information
    page_path = Column(String(500), nullable=False, index=True)
    page_title = Column(String(200))
    page_type = Column(String(50), index=True)  # jobs, profile, admin, etc.
    
    # Timing information
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    load_time = Column(Float)  # Page load time in seconds
    time_on_page = Column(Float)  # Time spent on page in seconds
    
    # Traffic source
    referrer = Column(Text)
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    
    # Device/Browser info
    device_type = Column(String(20))  # desktop, mobile, tablet
    browser = Column(String(50))
    os = Column(String(50))
    
    # Geographic data
    country = Column(String(50))
    region = Column(String(100))
    city = Column(String(100))
    
    __table_args__ = (
        Index('idx_pageview_path_time', 'page_path', 'timestamp'),
        Index('idx_pageview_user_time', 'user_id', 'timestamp'),
        Index('idx_pageview_daily', func.date(timestamp), 'page_path'),
    )


class UserSession(Base):
    """
    User session tracking for behavior analysis
    """
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(String(50), index=True)
    
    # Session timeline
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow, index=True)
    duration = Column(Float)  # Session duration in seconds
    
    # Session metrics
    page_views = Column(Integer, default=0)
    events_count = Column(Integer, default=0)
    pages_visited = Column(JSON, default=list)  # List of unique pages
    
    # Entry and exit
    landing_page = Column(String(500))
    exit_page = Column(String(500))
    referrer = Column(Text)
    
    # Device and location
    user_agent = Column(Text)
    ip_address = Column(String(45))
    country = Column(String(50))
    city = Column(String(100))
    
    # Conversion tracking
    converted = Column(Boolean, default=False)
    conversion_type = Column(String(50))  # job_application, registration, etc.
    conversion_value = Column(Float)
    
    __table_args__ = (
        Index('idx_session_user_started', 'user_id', 'started_at'),
        Index('idx_session_activity', 'last_activity'),
        Index('idx_session_daily', func.date(started_at)),
    )


class JobInteraction(Base):
    """
    Specific tracking for job-related interactions
    Key for employment portal analytics
    """
    __tablename__ = "job_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    job_id = Column(Integer, index=True)
    
    # Interaction details
    interaction_type = Column(String(50), nullable=False, index=True)  # view, apply, save, share
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Job details for analytics
    job_title = Column(String(200))
    job_category = Column(String(100), index=True)
    job_location = Column(String(100), index=True)
    job_type = Column(String(50))  # full-time, part-time, contract
    employer_type = Column(String(50))  # government, private
    
    # User context
    user_experience_level = Column(String(50))
    user_education = Column(String(100))
    user_location = Column(String(100))
    
    # Funnel tracking
    funnel_stage = Column(String(50))  # search, view, apply, interview, hired
    conversion_path = Column(JSON)  # Track user journey to this interaction
    
    __table_args__ = (
        Index('idx_job_interaction_type_time', 'interaction_type', 'timestamp'),
        Index('idx_job_interaction_category', 'job_category', 'timestamp'),
        Index('idx_job_interaction_user', 'user_id', 'job_id'),
    )


class UserBehaviorMetrics(Base):
    """
    Aggregated user behavior metrics for performance
    """
    __tablename__ = "user_behavior_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Activity metrics
    total_sessions = Column(Integer, default=0)
    total_page_views = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    avg_session_duration = Column(Float, default=0.0)
    
    # Job search behavior
    jobs_viewed = Column(Integer, default=0)
    jobs_applied = Column(Integer, default=0)
    jobs_saved = Column(Integer, default=0)
    search_queries = Column(Integer, default=0)
    
    # Engagement metrics
    first_visit = Column(DateTime, index=True)
    last_visit = Column(DateTime, index=True)
    days_active = Column(Integer, default=0)
    retention_score = Column(Float, default=0.0)
    
    # Conversion metrics
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    lifetime_value = Column(Float, default=0.0)
    
    # Demographics
    age_group = Column(String(20))
    gender = Column(String(10))
    education_level = Column(String(50))
    location = Column(String(100))
    
    # Preferences (learned from behavior)
    preferred_job_categories = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    preferred_job_types = Column(JSON, default=list)
    
    # Calculated fields
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_user_metrics_activity', 'last_visit', 'total_sessions'),
        Index('idx_user_metrics_conversion', 'conversion_rate', 'conversions'),
    )


class DailyAnalyticsSummary(Base):
    """
    Daily aggregated analytics for fast dashboard queries
    """
    __tablename__ = "daily_analytics_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # User metrics
    unique_visitors = Column(Integer, default=0)
    new_users = Column(Integer, default=0)
    returning_users = Column(Integer, default=0)
    total_sessions = Column(Integer, default=0)
    
    # Engagement metrics
    total_page_views = Column(Integer, default=0)
    avg_session_duration = Column(Float, default=0.0)
    bounce_rate = Column(Float, default=0.0)
    
    # Job portal specific
    job_searches = Column(Integer, default=0)
    job_views = Column(Integer, default=0)
    job_applications = Column(Integer, default=0)
    new_job_postings = Column(Integer, default=0)
    
    # Popular content
    top_pages = Column(JSON, default=list)
    top_search_terms = Column(JSON, default=list)
    top_job_categories = Column(JSON, default=list)
    
    # Traffic sources
    direct_traffic = Column(Integer, default=0)
    search_traffic = Column(Integer, default=0)
    social_traffic = Column(Integer, default=0)
    referral_traffic = Column(Integer, default=0)
    
    # Geographic distribution
    top_countries = Column(JSON, default=list)
    top_cities = Column(JSON, default=list)
    
    # Device breakdown
    desktop_users = Column(Integer, default=0)
    mobile_users = Column(Integer, default=0)
    tablet_users = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_daily_summary_date', 'date'),
    )


class RealTimeMetrics(Base):
    """
    Real-time metrics cache for live dashboard
    Updated every few minutes
    """
    __tablename__ = "realtime_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Metadata
    metric_type = Column(String(50))  # counter, gauge, histogram
    dimensions = Column(JSON, default=dict)  # Additional categorization
    
    __table_args__ = (
        Index('idx_realtime_name_time', 'metric_name', 'timestamp'),
    )


class ConversionFunnel(Base):
    """
    Track conversion funnels for job application process
    """
    __tablename__ = "conversion_funnels"
    
    id = Column(Integer, primary_key=True, index=True)
    funnel_name = Column(String(100), nullable=False, index=True)
    user_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    
    # Funnel steps
    step_name = Column(String(100), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Context
    job_id = Column(Integer, index=True)
    conversion_value = Column(Float)
    completed = Column(Boolean, default=False, index=True)
    
    # Timing
    time_to_convert = Column(Float)  # Seconds from funnel start to this step
    
    __table_args__ = (
        Index('idx_funnel_name_step', 'funnel_name', 'step_order'),
        Index('idx_funnel_completion', 'funnel_name', 'completed'),
    )
