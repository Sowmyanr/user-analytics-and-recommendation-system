"""
User management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_database
from app.models.user import User, UserProfile
from app.models.job import JobApplication, Job
from app.core.security import verify_token, hash_password
from app.analytics.tracker import get_analytics_tracker
from pydantic import BaseModel, EmailStr

router = APIRouter(tags=["users"])

# Pydantic schemas
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    resume_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    user_type: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    
    # Profile information
    full_name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[str] = None
    experience_years: Optional[int] = None
    education: Optional[str] = None
    resume_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None

class UserStatsResponse(BaseModel):
    user_id: str
    profile_completion: float
    total_applications: int
    active_applications: int
    jobs_posted: Optional[int] = None
    profile_views: int
    last_activity: Optional[datetime] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

async def get_current_user(token: str = Depends(verify_token), session: AsyncSession = Depends(get_database)):
    """Get current authenticated user"""
    user_result = await session.execute(select(User).where(User.id == token))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def calculate_profile_completion(user: User, profile: Optional[UserProfile]) -> float:
    """Calculate profile completion percentage"""
    total_fields = 10
    completed_fields = 0
    
    # User fields
    if user.email:
        completed_fields += 1
    
    if not profile:
        return (completed_fields / total_fields) * 100
    
    # Profile fields
    profile_fields = [
        profile.full_name,
        profile.phone,
        profile.location,
        profile.bio,
        profile.skills,
        profile.experience_years,
        profile.education,
        profile.resume_url,
        profile.portfolio_url
    ]
    
    completed_fields += sum(1 for field in profile_fields if field)
    
    return (completed_fields / total_fields) * 100

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
    analytics = Depends(get_analytics_tracker)
):
    """Get current user's profile"""
    
    # Get user profile
    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # Track analytics
    await analytics.track_event(
        user_id=current_user.id,
        event_name="profile_viewed",
        properties={
            "profile_completion": calculate_profile_completion(current_user, profile)
        }
    )
    
    response = UserResponse(
        id=current_user.id,
        email=current_user.email,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login
    )
    
    if profile:
        response.full_name = profile.full_name
        response.phone = profile.phone
        response.location = profile.location
        response.bio = profile.bio
        response.skills = profile.skills
        response.experience_years = profile.experience_years
        response.education = profile.education
        response.resume_url = profile.resume_url
        response.portfolio_url = profile.portfolio_url
        response.linkedin_url = profile.linkedin_url
    
    return response

@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
    analytics = Depends(get_analytics_tracker)
):
    """Update current user's profile"""
    
    # Get or create user profile
    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        session.add(profile)
    
    # Update profile with provided data
    update_data = profile_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    profile.updated_at = datetime.utcnow()
    current_user.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(profile)
    await session.refresh(current_user)
    
    # Track analytics
    await analytics.track_event(
        user_id=current_user.id,
        event_name="profile_updated",
        properties={
            "updated_fields": list(update_data.keys()),
            "profile_completion": calculate_profile_completion(current_user, profile)
        }
    )
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
        full_name=profile.full_name,
        phone=profile.phone,
        location=profile.location,
        bio=profile.bio,
        skills=profile.skills,
        experience_years=profile.experience_years,
        education=profile.education,
        resume_url=profile.resume_url,
        portfolio_url=profile.portfolio_url,
        linkedin_url=profile.linkedin_url
    )

@router.get("/me/stats", response_model=UserStatsResponse)
async def get_current_user_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database)
):
    """Get current user's statistics"""
    
    # Get profile for completion calculation
    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # Calculate profile completion
    profile_completion = calculate_profile_completion(current_user, profile)
    
    # Get application stats (for job seekers)
    total_applications = 0
    active_applications = 0
    if current_user.user_type == "job_seeker":
        total_apps_result = await session.execute(
            select(func.count(JobApplication.id)).where(JobApplication.applicant_id == current_user.id)
        )
        total_applications = total_apps_result.scalar() or 0
        
        active_apps_result = await session.execute(
            select(func.count(JobApplication.id)).where(
                and_(
                    JobApplication.applicant_id == current_user.id,
                    JobApplication.status.in_(["pending", "reviewed"])
                )
            )
        )
        active_applications = active_apps_result.scalar() or 0
    
    # Get jobs posted stats (for employers)
    jobs_posted = None
    if current_user.user_type == "employer":
        jobs_result = await session.execute(
            select(func.count(Job.id)).where(Job.posted_by == current_user.id)
        )
        jobs_posted = jobs_result.scalar() or 0
    
    # Get profile views (from analytics events)
    # This would typically come from your analytics data
    profile_views = 0  # Placeholder
    
    return UserStatsResponse(
        user_id=current_user.id,
        profile_completion=profile_completion,
        total_applications=total_applications,
        active_applications=active_applications,
        jobs_posted=jobs_posted,
        profile_views=profile_views,
        last_activity=current_user.last_login
    )

@router.post("/me/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
    analytics = Depends(get_analytics_tracker)
):
    """Change current user's password"""
    
    from app.core.security import verify_password
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = hash_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Track analytics
    await analytics.track_event(
        user_id=current_user.id,
        event_name="password_changed",
        properties={}
    )
    
    return {"message": "Password changed successfully"}

@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(
    user_id: str,
    session: AsyncSession = Depends(get_database),
    analytics = Depends(get_analytics_tracker)
):
    """Get a user's public profile"""
    
    # Get user
    user_result = await session.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user profile
    profile_result = await session.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = profile_result.scalar_one_or_none()
    
    # Track profile view
    await analytics.track_event(
        user_id=None,  # Anonymous view for now
        event_name="user_profile_viewed",
        properties={
            "viewed_user_id": user_id,
            "viewed_user_type": user.user_type
        }
    )
    
    response = UserResponse(
        id=user.id,
        email=user.email,  # In production, you might want to hide this
        user_type=user.user_type,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=None  # Hide last login from public profile
    )
    
    if profile:
        response.full_name = profile.full_name
        response.phone = None  # Hide phone from public profile
        response.location = profile.location
        response.bio = profile.bio
        response.skills = profile.skills
        response.experience_years = profile.experience_years
        response.education = profile.education
        response.resume_url = None  # Hide resume from public profile
        response.portfolio_url = profile.portfolio_url
        response.linkedin_url = profile.linkedin_url
    
    return response

@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_type: Optional[str] = None,
    location: Optional[str] = None,
    skills: Optional[str] = None,
    session: AsyncSession = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    """List users (for networking/recruitment purposes)"""
    
    # Build query
    query = select(User, UserProfile).outerjoin(UserProfile).where(User.is_active == True)
    
    if user_type:
        query = query.where(User.user_type == user_type)
    
    if location:
        query = query.where(UserProfile.location.ilike(f"%{location}%"))
    
    if skills:
        query = query.where(UserProfile.skills.ilike(f"%{skills}%"))
    
    # Order by creation date (newest first)
    query = query.order_by(desc(User.created_at))
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await session.execute(query)
    users_with_profiles = result.all()
    
    users = []
    for user, profile in users_with_profiles:
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            user_type=user.user_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=None  # Hide from public listing
        )
        
        if profile:
            user_response.full_name = profile.full_name
            user_response.location = profile.location
            user_response.bio = profile.bio
            user_response.skills = profile.skills
            user_response.experience_years = profile.experience_years
            user_response.education = profile.education
            user_response.portfolio_url = profile.portfolio_url
            user_response.linkedin_url = profile.linkedin_url
        
        users.append(user_response)
    
    return users

@router.delete("/me")
async def delete_current_user_account(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_database),
    analytics = Depends(get_analytics_tracker)
):
    """Delete current user's account"""
    
    # Mark user as inactive instead of hard delete to preserve data integrity
    current_user.is_active = False
    current_user.updated_at = datetime.utcnow()
    
    await session.commit()
    
    # Track analytics
    await analytics.track_event(
        user_id=current_user.id,
        event_type="account_deleted",
        properties={
            "user_type": current_user.user_type,
            "account_age_days": (datetime.utcnow() - current_user.created_at).days
        }
    )
    
    return {"message": "Account deactivated successfully"}
