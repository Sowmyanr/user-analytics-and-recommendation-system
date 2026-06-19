"""
Admin models for Punjab Rozgar Portal
Administrative functionality and system logging
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum
from typing import Dict, Any

from app.core.database import Base


class AdminRole(Enum):
    """Admin role levels"""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    ANALYST = "analyst"


class LogLevel(Enum):
    """System log levels"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AdminUser(Base):
    """
    Administrative users with enhanced permissions
    """
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(AdminRole), nullable=False, index=True)
    
    # Personal Information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    
    # Permissions
    permissions = Column(JSON, default=list)  # List of specific permissions
    can_manage_users = Column(Boolean, default=False)
    can_manage_jobs = Column(Boolean, default=False)
    can_view_analytics = Column(Boolean, default=True)
    can_moderate_content = Column(Boolean, default=False)
    can_access_system_logs = Column(Boolean, default=False)
    
    # Status
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, index=True)
    created_by = Column(String(50), index=True)  # Admin who created this account
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    account_locked = Column(Boolean, default=False)
    last_password_change = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_admin_role_active', 'role', 'active'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'admin_id': self.admin_id,
            'email': self.email,
            'role': self.role.value if self.role else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'permissions': self.permissions
        }
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class SystemLog(Base):
    """
    System activity and error logging
    """
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Log details
    level = Column(SQLEnum(LogLevel), nullable=False, index=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Context
    module = Column(String(100), index=True)  # Which part of system
    function = Column(String(100))
    line_number = Column(Integer)
    
    # User context
    user_id = Column(String(50), index=True)
    admin_id = Column(String(50), index=True)
    session_id = Column(String(100), index=True)
    
    # Request context
    request_id = Column(String(100), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_method = Column(String(10))
    request_path = Column(String(500))
    
    # Additional data
    extra_data = Column(JSON, default=dict)
    exception_type = Column(String(100))
    exception_traceback = Column(Text)
    
    __table_args__ = (
        Index('idx_log_level_time', 'level', 'timestamp'),
        Index('idx_log_module_time', 'module', 'timestamp'),
        Index('idx_log_user_time', 'user_id', 'timestamp'),
        Index('idx_log_daily', func.date(timestamp), 'level'),
    )


class AdminAction(Base):
    """
    Track administrative actions for audit trail
    """
    __tablename__ = "admin_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String(50), nullable=False, index=True)
    
    # Action details
    action_type = Column(String(100), nullable=False, index=True)
    action_description = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Target
    target_type = Column(String(50), index=True)  # user, job, application, etc.
    target_id = Column(String(50), index=True)
    
    # Context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(100))
    
    # Changes made
    before_data = Column(JSON, default=dict)
    after_data = Column(JSON, default=dict)
    
    # Result
    success = Column(Boolean, default=True, index=True)
    error_message = Column(Text)
    
    __table_args__ = (
        Index('idx_admin_action_type_time', 'action_type', 'timestamp'),
        Index('idx_admin_action_admin_time', 'admin_id', 'timestamp'),
        Index('idx_admin_action_target', 'target_type', 'target_id'),
    )


class SystemMetrics(Base):
    """
    System performance and health metrics
    """
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Metric details
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(String(500), nullable=False)  # JSON string for complex values
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Categorization
    category = Column(String(50), index=True)  # performance, database, api, etc.
    severity = Column(String(20), index=True)  # normal, warning, critical
    
    # Additional context
    metrics_metadata = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_metrics_name_time', 'metric_name', 'timestamp'),
        Index('idx_metrics_category_severity', 'category', 'severity'),
    )


class ContentModeration(Base):
    """
    Content moderation tracking
    """
    __tablename__ = "content_moderation"
    
    id = Column(Integer, primary_key=True, index=True)
    moderator_id = Column(String(50), nullable=False, index=True)
    
    # Content details
    content_type = Column(String(50), nullable=False, index=True)  # job, profile, comment
    content_id = Column(String(50), nullable=False, index=True)
    
    # Moderation action
    action = Column(String(50), nullable=False, index=True)  # approve, reject, flag
    reason = Column(String(200))
    notes = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Automated vs manual
    automated = Column(Boolean, default=False, index=True)
    confidence_score = Column(Integer)  # For automated moderation
    
    __table_args__ = (
        Index('idx_moderation_content', 'content_type', 'content_id'),
        Index('idx_moderation_moderator_time', 'moderator_id', 'timestamp'),
        Index('idx_moderation_action_time', 'action', 'timestamp'),
    )


class BackupLog(Base):
    """
    Database backup and maintenance logs
    """
    __tablename__ = "backup_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Backup details
    backup_type = Column(String(50), nullable=False, index=True)  # full, incremental
    status = Column(String(20), nullable=False, index=True)  # success, failed, in_progress
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime)
    
    # Size and location
    backup_size = Column(Integer)  # Bytes
    backup_location = Column(String(500))
    
    # Results
    tables_backed_up = Column(Integer)
    records_backed_up = Column(Integer)
    error_message = Column(Text)
    
    # Metadata
    triggered_by = Column(String(50))  # admin_id or 'system'
    backup_metadata = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('idx_backup_type_status', 'backup_type', 'status'),
        Index('idx_backup_started', 'started_at'),
    )


class SystemConfig(Base):
    """System configuration settings"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text)
    config_type = Column(String(50), default="string")  # string, number, boolean, json
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(50))  # admin_id
