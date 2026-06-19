"""
User models for Punjab Rozgar Portal
Authentication and user management with analytics integration
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from app.core.database import Base


class UserRole(Enum):
    """User role enumeration"""
    JOB_SEEKER = "job_seeker"
    EMPLOYER = "employer" 
    ADMIN = "admin"
    MODERATOR = "moderator"


class AccountStatus(Enum):
    """Account status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"


class User(Base):
    """
    Main user model for job seekers and employers
    Optimized for analytics tracking
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)  # Public user ID
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), index=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.JOB_SEEKER, index=True)
    status = Column(SQLEnum(AccountStatus), default=AccountStatus.PENDING_VERIFICATION, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime)
    gender = Column(String(10))
    
    # Location
    address = Column(Text)
    city = Column(String(100), index=True)
    state = Column(String(100), default="Punjab", index=True)
    pincode = Column(String(10), index=True)
    
    # Professional Information
    education_level = Column(String(100), index=True)
    experience_years = Column(Integer, index=True)
    current_job_title = Column(String(200))
    skills = Column(JSON, default=list)  # List of skills
    preferred_job_categories = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    
    # Account Management
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, index=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    
    # Analytics Integration
    signup_source = Column(String(100))  # How they found the portal
    utm_source = Column(String(100))
    utm_medium = Column(String(100))
    utm_campaign = Column(String(100))
    
    # Profile Completion
    profile_completion_score = Column(Integer, default=0)  # 0-100
    resume_uploaded = Column(Boolean, default=False)
    photo_uploaded = Column(Boolean, default=False)
    
    # Privacy Settings
    profile_public = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    
    # Employer-specific fields
    company_name = Column(String(200), index=True)
    company_size = Column(String(50))
    industry = Column(String(100), index=True)
    company_description = Column(Text)
    company_website = Column(String(255))
    
    # Analytics tracking fields
    total_applications = Column(Integer, default=0)
    total_job_views = Column(Integer, default=0)
    total_searches = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_user_role_status', 'role', 'status'),
        Index('idx_user_location', 'city', 'state'),
        Index('idx_user_education_exp', 'education_level', 'experience_years'),
        Index('idx_user_created', 'created_at'),
        Index('idx_user_employer', 'role', 'company_name'),
    )
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Convert user to dictionary for API responses"""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'email': self.email if include_sensitive else self.email,
            'phone': self.phone if include_sensitive else None,
            'role': self.role.value if self.role else None,
            'status': self.status.value if self.status else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'name': self.full_name,  # Add name field for frontend compatibility
            'city': self.city,
            'state': self.state,
            'education_level': self.education_level,
            'experience_years': self.experience_years,
            'skills': self.skills,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'profile_completion_score': self.profile_completion_score,
            'company_name': self.company_name if self.role == UserRole.EMPLOYER else None
        }
        return {k: v for k, v in data.items() if v is not None}
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_job_seeker(self) -> bool:
        """Check if user is a job seeker"""
        return self.role == UserRole.JOB_SEEKER
    
    @property
    def is_employer(self) -> bool:
        """Check if user is an employer"""
        return self.role == UserRole.EMPLOYER
    
    @property
    def is_admin(self) -> bool:
        """Check if user is an admin"""
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR]


class UserProfile(Base):
    """
    Extended user profile information
    Separated for performance optimization
    """
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Detailed Profile
    about = Column(Text)
    resume_url = Column(String(500))
    portfolio_url = Column(String(500))
    linkedin_url = Column(String(500))
    photo_url = Column(String(500))
    
    # Work Experience
    work_experience = Column(JSON, default=list)  # List of work experiences
    education_details = Column(JSON, default=list)  # List of education
    certifications = Column(JSON, default=list)  # List of certifications
    languages = Column(JSON, default=list)  # Languages known
    
    # Job Preferences
    expected_salary_min = Column(Integer)
    expected_salary_max = Column(Integer)
    preferred_job_type = Column(String(50))  # full-time, part-time, etc.
    willing_to_relocate = Column(Boolean, default=False)
    notice_period = Column(String(50))  # immediate, 1 month, etc.
    
    # Additional Information
    hobbies = Column(JSON, default=list)
    achievements = Column(JSON, default=list)
    references = Column(JSON, default=list)
    
    # Privacy and Visibility
    profile_visibility = Column(String(20), default="public")  # public, private, recruiter_only
    allow_recruiter_contact = Column(Boolean, default=True)
    show_salary_expectations = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_profile_visibility', 'profile_visibility'),
    )


class UserActivity(Base):
    """
    Track user activities for analytics and recommendations
    """
    __tablename__ = "user_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Activity Details
    activity_type = Column(String(100), nullable=False, index=True)
    activity_data = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Context
    session_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    __table_args__ = (
        Index('idx_activity_user_type_time', 'user_id', 'activity_type', 'timestamp'),
        Index('idx_activity_daily', func.date(timestamp), 'activity_type'),
    )


class UserPreferences(Base):
    """
    User preferences and settings
    """
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Job Alert Preferences
    job_alerts_enabled = Column(Boolean, default=True)
    alert_frequency = Column(String(20), default="daily")  # daily, weekly, immediate
    alert_keywords = Column(JSON, default=list)
    alert_locations = Column(JSON, default=list)
    alert_categories = Column(JSON, default=list)
    
    # Communication Preferences
    email_job_matches = Column(Boolean, default=True)
    email_application_updates = Column(Boolean, default=True)
    email_newsletter = Column(Boolean, default=False)
    sms_urgent_notifications = Column(Boolean, default=False)
    
    # Privacy Preferences
    profile_searchable = Column(Boolean, default=True)
    contact_info_visible = Column(Boolean, default=False)
    allow_analytics_tracking = Column(Boolean, default=True)
    
    # Display Preferences
    preferred_language = Column(String(10), default="en")
    timezone = Column(String(50), default="Asia/Kolkata")
    currency = Column(String(10), default="INR")
    
    # Updated timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserVerification(Base):
    """
    User verification status and tokens
    """
    __tablename__ = "user_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    
    # Verification Types
    verification_type = Column(String(50), nullable=False, index=True)  # email, phone, document
    verification_token = Column(String(255), unique=True)
    verified = Column(Boolean, default=False, index=True)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    expires_at = Column(DateTime, index=True)
    
    # Additional data
    verification_data = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_verification_user_type', 'user_id', 'verification_type'),
        Index('idx_verification_token', 'verification_token'),
    )
