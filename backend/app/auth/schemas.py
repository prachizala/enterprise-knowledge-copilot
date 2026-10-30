"""Pydantic schemas for authentication and RBAC."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field



class UserRegisterRequest(BaseModel):
    """Payload to register a new enterprise user."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    name: Optional[str] = None
    role: str = Field("EMPLOYEE", description="ADMIN, MANAGER, EMPLOYEE, VIEWER")
    department: str = Field("General", description="Department affiliation")

    def model_post_init(self, __context: object) -> None:
        if not self.full_name and self.name:
            self.full_name = self.name
        elif not self.full_name:
            self.full_name = self.email.split("@")[0]


class UserLoginRequest(BaseModel):
    """Payload to authenticate user."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT Bearer access token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: str
    email: str
    full_name: str
    role: str
    department: str


class UserResponse(BaseModel):
    """Public user profile response."""
    id: str
    email: str
    full_name: str
    role: str
    department: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
