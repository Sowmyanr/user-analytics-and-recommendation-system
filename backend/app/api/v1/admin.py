"""
Admin management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, update, delete
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_database
from app.models.user import User, UserProfile, UserRole
from app.models.job import Job, JobApplication, JobStatus
from app.models.admin import AdminAction, SystemConfig
from app.models.analytics import AnalyticsEvent
from app.core.security import verify_token
from app.analytics.tracker import get_analytics_tracker
from pydantic import BaseModel

router = APIRouter(tags=["admin"])
security = HTTPBearer()

# Pydantic schemas
class AdminStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_jobs: int
    active_jobs: int
    total_applications: int
    pending_applications: int
    recent_signups: int
    recent_job_posts: int

class UserManagementResponse(BaseModel):
    id: str
    email: str
    user_type: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    total_applications: Optional[int] = None
    total_jobs_posted: Optional[int] = None

class JobManagementResponse(BaseModel):
    job_id: str
    title: str
    employer_name: str
    location_city: str
    job_type: Optional[str] = None
    status: str
    created_at: datetime
    employer_id: str
    application_count: int

class AdminActionResponse(BaseModel):
    id: str
    admin_id: str
    action_type: str
    target_type: str
    target_id: str
    description: str
    created_at: datetime

class SystemConfigUpdate(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class UserStatusUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_database)
):
    """Get current authenticated admin user via Bearer token"""
    user_id = verify_token(credentials.credentials)
    user_result = await session.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role not in [UserRole.ADMIN, UserRole.MODERATOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return user

async def log_admin_action(
    session: AsyncSession,
    admin_id: str,
    action_type: str,
    target_type: str,
    target_id: str,
    description: str
):
    """Log admin action"""
    # Align with AdminAction model field names
    admin_action = AdminAction(
        admin_id=admin_id,
        action_type=action_type,
        action_description=description,
        target_type=target_type,
        target_id=target_id
    )
    session.add(admin_action)
    await session.commit()

@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin)
):
    """Get system statistics for admin dashboard"""
    
    # Total users
    total_users_result = await session.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Active users
    active_users_result = await session.execute(
        select(func.count(User.id)).where(User.is_active == True)
    )
    active_users = active_users_result.scalar() or 0
    
    # Total jobs
    total_jobs_result = await session.execute(select(func.count(Job.id)))
    total_jobs = total_jobs_result.scalar() or 0
    
    # Active jobs
    active_jobs_result = await session.execute(
        select(func.count(Job.id)).where(Job.is_active == True)
    )
    active_jobs = active_jobs_result.scalar() or 0
    
    # Total applications
    total_applications_result = await session.execute(select(func.count(JobApplication.id)))
    total_applications = total_applications_result.scalar() or 0
    
    # Pending applications
    pending_applications_result = await session.execute(
        select(func.count(JobApplication.id)).where(JobApplication.status == "pending")
    )
    pending_applications = pending_applications_result.scalar() or 0
    
    # Recent signups (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_signups_result = await session.execute(
        select(func.count(User.id)).where(User.created_at >= seven_days_ago)
    )
    recent_signups = recent_signups_result.scalar() or 0
    
    # Recent job posts (last 7 days)
    recent_jobs_result = await session.execute(
        select(func.count(Job.id)).where(Job.created_at >= seven_days_ago)
    )
    recent_job_posts = recent_jobs_result.scalar() or 0
    
    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_applications=total_applications,
        pending_applications=pending_applications,
        recent_signups=recent_signups,
        recent_job_posts=recent_job_posts
    )

@router.get("/users", response_model=List[UserManagementResponse])
async def list_users_for_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin)
):
    """List all users for admin management"""
    
    # Build query
    query = select(User)
    
    if user_type:
        query = query.where(User.user_type == user_type)
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    if is_verified is not None:
        query = query.where(User.is_verified == is_verified)
    
    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.id.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(desc(User.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    # Get additional stats for each user
    user_responses = []
    for user in users:
        user_response = UserManagementResponse(
            id=user.id,
            email=user.email,
            user_type=user.user_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
        # Get user-specific stats
        if user.user_type == "job_seeker":
            apps_result = await session.execute(
                select(func.count(JobApplication.id)).where(JobApplication.applicant_id == user.id)
            )
            user_response.total_applications = apps_result.scalar() or 0
        
        elif user.user_type == "employer":
            jobs_result = await session.execute(
                select(func.count(Job.id)).where(Job.posted_by == user.id)
            )
            user_response.total_jobs_posted = jobs_result.scalar() or 0
        
        user_responses.append(user_response)
    
    return user_responses

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    status_update: UserStatusUpdate,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
    analytics = Depends(get_analytics_tracker)
):
    """Update user status (activate/deactivate, verify/unverify)"""
    
    # Get user
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user status
    update_data = status_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(user)
    
    # Log admin action
    await log_admin_action(
        session=session,
        admin_id=current_admin.id,
        action_type="user_status_update",
        target_type="user",
        target_id=user_id,
        description=f"Updated user status: {update_data}"
    )
    
    # Track analytics
    await analytics.track_event(
        user_id=current_admin.id,
        event_name="admin_user_status_updated",
        properties={
            "target_user_id": user_id,
            "changes": update_data
        }
    )
    
    return {"message": "User status updated successfully"}

@router.get("/jobs", response_model=List[JobManagementResponse])
async def list_jobs_for_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: Optional[str] = None,
    job_type: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin)
):
    """List all jobs for admin management"""
    
    # Build query
    query = select(Job)
    
    if status_filter:
        try:
            js = JobStatus(status_filter)
            query = query.where(Job.status == js)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job status filter")
    
    if job_type:
        try:
            from app.models.job import JobType
            jt = JobType(job_type)
            query = query.where(Job.job_type == jt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid job type filter")
    
    if search:
        search_filter = or_(
            Job.title.ilike(f"%{search}%"),
            Job.employer_name.ilike(f"%{search}%"),
            Job.location_city.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(desc(Job.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    jobs = result.scalars().all()
    
    # Get stats for each job
    job_responses = []
    for job in jobs:
        # Get application count
        app_count_result = await session.execute(
            select(func.count(JobApplication.id)).where(JobApplication.job_id == job.job_id)
        )
        application_count = app_count_result.scalar() or 0
        
        job_responses.append(JobManagementResponse(
            job_id=job.job_id,
            title=job.title,
            employer_name=job.employer_name,
            location_city=job.location_city,
            job_type=job.job_type.value if job.job_type else None,
            status=job.status.value if job.status else "draft",
            created_at=job.created_at,
            employer_id=job.employer_id,
            application_count=application_count
        ))
    
    return job_responses

class UpdateJobStatus(BaseModel):
    status: str

@router.put("/jobs/{job_id}/status")
async def update_job_status(
    job_id: str,
    payload: UpdateJobStatus,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
    analytics = Depends(get_analytics_tracker)
):
    """Update job status (approve/pause/close). Uses public job_id."""

    # Get job by public job_id
    job_result = await session.execute(select(Job).where(Job.job_id == job_id))
    job = job_result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Validate and set status
    try:
        new_status = JobStatus(payload.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job status")

    job.status = new_status
    if new_status == JobStatus.ACTIVE and not job.published_at:
        job.published_at = datetime.utcnow()
    job.updated_at = datetime.utcnow()

    await session.commit()

    # Log admin action
    await log_admin_action(
        session=session,
        admin_id=current_admin.id,
        action_type="job_status_update",
        target_type="job",
        target_id=job.job_id,
        description=f"Set job status to: {new_status.value}"
    )

    # Track analytics
    await analytics.track_event(
        user_id=current_admin.id,
        event_name="admin_job_status_updated",
        properties={
            "job_id": job.job_id,
            "status": new_status.value,
            "job_title": job.title
        }
    )

    return {"message": "Job status updated successfully", "job_id": job.job_id, "status": new_status.value}

@router.delete("/jobs/{job_id}")
async def delete_job_admin(
    job_id: str,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
    analytics = Depends(get_analytics_tracker)
):
    """Delete a job (admin only)"""
    
    # Get job by public job_id
    job_result = await session.execute(select(Job).where(Job.job_id == job_id))
    job = job_result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_title = job.title
    
    # Delete job (cascade will handle applications)
    await session.delete(job)
    await session.commit()
    
    # Log admin action
    await log_admin_action(
        session=session,
        admin_id=current_admin.id,
        action_type="job_delete",
        target_type="job",
        target_id=job_id,
        description=f"Deleted job: {job_title}"
    )
    
    # Track analytics
    await analytics.track_event(
        user_id=current_admin.id,
        event_name="admin_job_deleted",
        properties={
            "job_id": job_id,
            "job_title": job_title
        }
    )
    
    return {"message": "Job deleted successfully"}

@router.get("/actions", response_model=List[AdminActionResponse])
async def get_admin_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    action_type: Optional[str] = None,
    target_type: Optional[str] = None,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin)
):
    """Get admin action log"""
    
    query = select(AdminAction)
    
    if action_type:
        query = query.where(AdminAction.action_type == action_type)
    
    if target_type:
        query = query.where(AdminAction.target_type == target_type)
    
    query = query.order_by(desc(AdminAction.created_at)).offset(skip).limit(limit)
    
    result = await session.execute(query)
    actions = result.scalars().all()
    
    return [
        AdminActionResponse(
            id=action.id,
            admin_id=action.admin_id,
            action_type=action.action_type,
            target_type=action.target_type,
            target_id=action.target_id,
            description=action.description,
            created_at=action.created_at
        )
        for action in actions
    ]

@router.get("/system/config")
async def get_system_config(
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin)
):
    """Get system configuration"""
    
    result = await session.execute(select(SystemConfig))
    configs = result.scalars().all()
    
    return {config.key: {"value": config.value, "description": config.description} for config in configs}

@router.put("/system/config")
async def update_system_config(
    config_update: SystemConfigUpdate,
    session: AsyncSession = Depends(get_database),
    current_admin: User = Depends(get_current_admin),
    analytics = Depends(get_analytics_tracker)
):
    """Update system configuration"""
    
    # Get or create config
    config_result = await session.execute(
        select(SystemConfig).where(SystemConfig.key == config_update.key)
    )
    config = config_result.scalar_one_or_none()
    
    if not config:
        config = SystemConfig(
            key=config_update.key,
            value=config_update.value,
            description=config_update.description
        )
        session.add(config)
    else:
        config.value = config_update.value
        if config_update.description:
            config.description = config_update.description
        config.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Log admin action
    await log_admin_action(
        session=session,
        admin_id=current_admin.id,
        action_type="system_config_update",
        target_type="config",
        target_id=config_update.key,
        description=f"Updated config {config_update.key} to {config_update.value}"
    )
    
    # Track analytics
    await analytics.track_event(
        user_id=current_admin.id,
        event_name="admin_config_updated",
        properties={
            "config_key": config_update.key,
            "config_value": config_update.value
        }
    )
    
    return {"message": "Configuration updated successfully"}
