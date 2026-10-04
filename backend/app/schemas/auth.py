"""
Pydantic schemas for User Authentication (Signup, Login, Profile).
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class UserSignUp(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="User full name")
    email: EmailStr = Field(..., description="User valid email address")
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Password (minimum 6 characters)",
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="User registered email")
    password: str = Field(..., min_length=1, description="Password")


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    message: Optional[str] = "Success"
