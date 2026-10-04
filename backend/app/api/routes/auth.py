"""
TruthLens – Authentication API Routes.
Provides signup, login, get current user (me), and logout endpoints.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User
from app.schemas.auth import (
    AuthResponse,
    UserLogin,
    UserResponse,
    UserSignUp,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that extracts and validates the Bearer JWT token from headers."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1].strip()
    email = decode_access_token(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.email == email.lower().strip())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: UserSignUp, db: AsyncSession = Depends(get_db)):
    """
    Register a new user account.
    Validates email uniqueness and hashes password with native bcrypt.
    """
    clean_email = payload.email.lower().strip()

    # Check for existing email
    stmt = select(User).where(User.email == clean_email)
    existing_user = (await db.execute(stmt)).scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    # Create user
    hashed = hash_password(payload.password)
    new_user = User(
        name=payload.name.strip(),
        email=clean_email,
        hashed_password=hashed,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    token = create_access_token(new_user.email)
    logger.info("New user registered successfully: %s (id=%d)", new_user.email, new_user.id)

    return AuthResponse(
        user=UserResponse.model_validate(new_user),
        access_token=token,
        token_type="bearer",
        message="Account created successfully",
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate an existing user with email and password.
    Returns JWT access token on success.
    """
    clean_email = payload.email.lower().strip()

    stmt = select(User).where(User.email == clean_email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please try again.",
        )

    token = create_access_token(user.email)
    logger.info("User logged in successfully: %s", user.email)

    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=token,
        token_type="bearer",
        message="Logged in successfully",
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile information of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout():
    """Endpoint for user logout."""
    return {"message": "Logged out successfully"}
