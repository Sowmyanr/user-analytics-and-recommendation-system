"""
Authentication API Routes
User registration, login, and authentication management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
from typing import Optional
import uuid
import logging

from app.core.database import get_database
from app.models.user import User, UserRole, AccountStatus
from app.core.security import hash_password, verify_password, create_access_token, verify_token

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# ============================================================================
# Pydantic Models
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None
    role: str = Field(default="job_seeker", description="job_seeker or employer")
    city: Optional[str] = None
    
class UserLoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str

class AuthResponse(BaseModel):
    """Authentication response"""
    success: bool
    message: str
    access_token: Optional[str] = None
    user: Optional[dict] = None

# ============================================================================
# Authentication Routes
# ============================================================================

@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """Register a new user"""
    try:
        # Check if user already exists
        existing_user = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        # Validate role
        if user_data.role not in ["job_seeker", "employer"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be 'job_seeker' or 'employer'"
            )
        
        # Create new user
        user_role = UserRole.JOB_SEEKER if user_data.role == "job_seeker" else UserRole.EMPLOYER
        hashed_pw = hash_password(user_data.password)
        
        new_user = User(
            user_id=f"user_{uuid.uuid4().hex[:12]}",
            email=user_data.email,
            hashed_password=hashed_pw,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=user_role,
            city=user_data.city,
            status=AccountStatus.PENDING_VERIFICATION
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create access token
        access_token = create_access_token(data={"sub": new_user.user_id})
        
        # Track registration event
        if hasattr(request.app.state, 'analytics'):
            await request.app.state.analytics.track_event(
                event_name="user_registration",
                properties={
                    "role": user_data.role,
                    "city": user_data.city,
                    "registration_method": "email"
                },
                user_id=new_user.user_id,
                request=request
            )
        
        return AuthResponse(
            success=True,
            message="User registered successfully",
            access_token=access_token,
            user=new_user.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=AuthResponse)
async def login_user(
    login_data: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_database)
):
    """User login"""
    try:
        # Find user
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check account status
        if user.status == AccountStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is suspended"
            )
        
        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()
        
        # Create access token
        access_token = create_access_token(data={"sub": user.user_id})
        
        # Track login event
        if hasattr(request.app.state, 'analytics'):
            await request.app.state.analytics.track_event(
                event_name="user_login",
                properties={
                    "role": user.role.value,
                    "login_method": "email"
                },
                user_id=user.user_id,
                request=request
            )
        
        return AuthResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            user=user.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/logout")
async def logout_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database)
):
    """User logout"""
    try:
        # In a real implementation, you might want to blacklist the token
        # For now, we'll just track the logout event
        
        user_id = verify_token(credentials.credentials)
        
        if hasattr(request.app.state, 'analytics'):
            await request.app.state.analytics.track_event(
                event_name="user_logout",
                properties={},
                user_id=user_id,
                request=request
            )
        
        return {"success": True, "message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return {"success": True, "message": "Logged out"}  # Always succeed for logout

@router.get("/me")
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_database)
):
    """Get current user information"""
    try:
        user_id = verify_token(credentials.credentials)
        
        result = await db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "success": True,
            "user": user.to_dict(include_sensitive=True)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )
