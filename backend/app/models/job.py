"""
Job models for Punjab Rozgar Portal
Job postings, applications, and related functionality with analytics
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List

from app.core.database import Base


class JobType(Enum):
    """Job type enumeration"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class JobStatus(Enum):
    """Job posting status"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"
    EXPIRED = "expired"


class EmployerType(Enum):
    """Employer type for government portal"""
    GOVERNMENT = "government"
    PUBLIC_SECTOR = "public_sector"
    PRIVATE = "private"
    NGO = "ngo"
    STARTUP = "startup"


class ApplicationStatus(Enum):
    """Job application status"""
    APPLIED = "applied"
    REVIEWED = "reviewed"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    SELECTED = "selected"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Job(Base):
    """
    Main job posting model with analytics tracking
    """
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)  # Public job ID
    
    # Basic Information
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text)
    responsibilities = Column(Text)
    
    # Job Details
    job_type = Column(SQLEnum(JobType), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), index=True)
    
    # Location
    location_city = Column(String(100), nullable=False, index=True)
    location_state = Column(String(100), default="Punjab", index=True)
    location_area = Column(String(200))
    remote_allowed = Column(Boolean, default=False, index=True)
    
    # Compensation
    salary_min = Column(Integer, index=True)
    salary_max = Column(Integer, index=True)
    salary_currency = Column(String(10), default="INR")
    salary_period = Column(String(20), default="monthly")  # monthly, yearly, hourly
    
    # Experience and Education
    experience_min = Column(Integer, default=0, index=True)
    experience_max = Column(Integer, index=True)
    education_level = Column(String(100), index=True)
    skills_required = Column(JSON, default=list)
    skills_preferred = Column(JSON, default=list)
    
    # Employer Information
    employer_id = Column(String(50), nullable=False, index=True)
    employer_name = Column(String(200), nullable=False, index=True)
    employer_type = Column(SQLEnum(EmployerType), nullable=False, index=True)
    company_size = Column(String(50))
    
    # Application Details
    application_deadline = Column(DateTime, index=True)
    application_method = Column(String(50), default="online")  # online, email, offline
    application_url = Column(String(500))
    contact_email = Column(String(255))
    contact_phone = Column(String(20))
    
    # Status and Lifecycle
    status = Column(SQLEnum(JobStatus), default=JobStatus.DRAFT, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, index=True)
    expires_at = Column(DateTime, index=True)
    
    # Analytics Fields
    views_count = Column(Integer, default=0, index=True)
    applications_count = Column(Integer, default=0, index=True)
    shares_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    
    # SEO and Metadata
    slug = Column(String(300), unique=True, index=True)
    meta_description = Column(String(500))
    featured = Column(Boolean, default=False, index=True)
    urgent = Column(Boolean, default=False, index=True)
    
    # Government Job Specific
    government_scheme = Column(String(100), index=True)  # PGRKAM, etc.
    reservation_category = Column(JSON, default=list)  # SC, ST, OBC, etc.
    age_limit_min = Column(Integer)
    age_limit_max = Column(Integer)
    
    # Additional Information
    benefits = Column(JSON, default=list)
    working_hours = Column(String(100))
    interview_process = Column(Text)
    additional_info = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_job_location_type', 'location_city', 'job_type'),
        Index('idx_job_category_status', 'category', 'status'),
        Index('idx_job_employer_status', 'employer_id', 'status'),
        Index('idx_job_published', 'published_at', 'status'),
        Index('idx_job_analytics', 'views_count', 'applications_count'),
        Index('idx_job_search', 'title', 'category', 'location_city'),
    )
    
    def to_dict(self, include_analytics: bool = False) -> Dict[str, Any]:
        """Convert job to dictionary for API responses"""
        data = {
            'job_id': self.job_id,
            'title': self.title,
            'description': self.description,
            'job_type': self.job_type.value if self.job_type else None,
            'category': self.category,
            'location_city': self.location_city,
            'location_state': self.location_state,
            'remote_allowed': self.remote_allowed,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'experience_min': self.experience_min,
            'experience_max': self.experience_max,
            'education_level': self.education_level,
            'employer_name': self.employer_name,
            'employer_type': self.employer_type.value if self.employer_type else None,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'status': self.status.value if self.status else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'featured': self.featured,
            'urgent': self.urgent
        }
        
        if include_analytics:
            data.update({
                'views_count': self.views_count,
                'applications_count': self.applications_count,
                'shares_count': self.shares_count,
                'saves_count': self.saves_count
            })
        
        return data
    
    @property
    def is_active(self) -> bool:
        """Check if job is currently active"""
        return (
            self.status == JobStatus.ACTIVE and
            (self.expires_at is None or self.expires_at > datetime.utcnow()) and
            (self.application_deadline is None or self.application_deadline > datetime.utcnow())
        )
    
    @property
    def is_government(self) -> bool:
        """Check if this is a government job"""
        return self.employer_type in [EmployerType.GOVERNMENT, EmployerType.PUBLIC_SECTOR]
    
    @property
    def days_until_deadline(self) -> Optional[int]:
        """Get days until application deadline"""
        if not self.application_deadline:
            return None
        delta = self.application_deadline - datetime.utcnow()
        return max(0, delta.days)


class JobApplication(Base):
    """
    Job applications with comprehensive tracking
    """
    __tablename__ = "job_applications"
    
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Relations
    job_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Application Details
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.APPLIED, index=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Application Materials
    resume_url = Column(String(500))
    cover_letter = Column(Text)
    portfolio_url = Column(String(500))
    additional_documents = Column(JSON, default=list)
    
    # Applicant Information (snapshot at time of application)
    applicant_name = Column(String(200), nullable=False)
    applicant_email = Column(String(255), nullable=False)
    applicant_phone = Column(String(20))
    applicant_experience = Column(Integer)
    applicant_location = Column(String(100))
    applicant_skills = Column(JSON, default=list)
    
    # Employer Actions
    viewed_by_employer = Column(Boolean, default=False, index=True)
    employer_notes = Column(Text)
    rating = Column(Integer)  # 1-5 rating by employer
    
    # Interview Information
    interview_scheduled = Column(Boolean, default=False)
    interview_date = Column(DateTime)
    interview_mode = Column(String(50))  # online, offline, phone
    interview_location = Column(String(200))
    interview_notes = Column(Text)
    
    # Outcome
    selected = Column(Boolean, default=False, index=True)
    rejection_reason = Column(String(100))
    feedback = Column(Text)
    
    # Analytics
    source = Column(String(100))  # How they found this job
    time_to_apply = Column(Integer)  # Seconds from job view to application
    session_id = Column(String(100))
    
    __table_args__ = (
        Index('idx_application_job_status', 'job_id', 'status'),
        Index('idx_application_user_status', 'user_id', 'status'),
        Index('idx_application_employer', 'job_id', 'viewed_by_employer'),
        Index('idx_application_timeline', 'applied_at', 'status'),
    )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert application to dictionary"""
        data = {
            'application_id': self.application_id,
            'job_id': self.job_id,
            'status': self.status.value if self.status else None,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None,
            'applicant_name': self.applicant_name,
            'selected': self.selected
        }
        
        if include_sensitive:
            data.update({
                'applicant_email': self.applicant_email,
                'applicant_phone': self.applicant_phone,
                'cover_letter': self.cover_letter,
                'employer_notes': self.employer_notes,
                'rating': self.rating,
                'feedback': self.feedback
            })
        
        return data


class SavedJob(Base):
    """
    Jobs saved by users for later application
    """
    __tablename__ = "saved_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    job_id = Column(String(50), nullable=False, index=True)
    
    # Metadata
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text)  # User's personal notes about the job
    applied = Column(Boolean, default=False, index=True)
    
    __table_args__ = (
        Index('idx_saved_user_job', 'user_id', 'job_id'),
        Index('idx_saved_applied', 'user_id', 'applied'),
    )


class JobAlert(Base):
    """
    Job alerts based on user preferences
    """
    __tablename__ = "job_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Alert Configuration
    alert_name = Column(String(100), nullable=False)
    keywords = Column(JSON, default=list)
    categories = Column(JSON, default=list)
    locations = Column(JSON, default=list)
    job_types = Column(JSON, default=list)
    
    # Filters
    salary_min = Column(Integer)
    experience_min = Column(Integer)
    experience_max = Column(Integer)
    remote_only = Column(Boolean, default=False)
    
    # Frequency
    frequency = Column(String(20), default="daily")  # immediate, daily, weekly
    active = Column(Boolean, default=True, index=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sent = Column(DateTime)
    total_sent = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_alert_user_active', 'user_id', 'active'),
    )


class JobView(Base):
    """
    Track job views for analytics
    """
    __tablename__ = "job_views"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), index=True)  # Null for anonymous users
    session_id = Column(String(100), index=True)
    
    # View details
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    time_spent = Column(Integer)  # Seconds spent viewing
    referrer = Column(String(500))
    search_query = Column(String(200))
    
    # Device/Location
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_type = Column(String(20))
    
    __table_args__ = (
        Index('idx_jobview_job_time', 'job_id', 'viewed_at'),
        Index('idx_jobview_user_time', 'user_id', 'viewed_at'),
        Index('idx_jobview_daily', func.date(viewed_at), 'job_id'),
    )


class JobCategory(Base):
    """
    Job categories for organization and analytics
    """
    __tablename__ = "job_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    
    # Hierarchy
    parent_id = Column(Integer, ForeignKey('job_categories.id'), index=True)
    level = Column(Integer, default=0, index=True)
    
    # Display
    icon = Column(String(100))
    color = Column(String(20))
    order = Column(Integer, default=0, index=True)
    
    # Analytics
    jobs_count = Column(Integer, default=0, index=True)
    popular = Column(Boolean, default=False, index=True)
    
    # Status
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_category_parent_order', 'parent_id', 'order'),
        Index('idx_category_active_popular', 'active', 'popular'),
    )
