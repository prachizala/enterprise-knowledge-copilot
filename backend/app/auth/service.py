"""Authentication and user management service."""

import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import UserRegisterRequest
from app.auth.security import hash_password, verify_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user registration, authentication, and retrieval."""

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Look up user by unique email."""
        stmt = select(User).where(User.email == email.strip().lower())
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """Look up user by ID."""
        stmt = select(User).where(User.id == user_id)
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def register(db: AsyncSession, payload: UserRegisterRequest) -> User:
        """Register a new user account with hashed password."""
        normalized_email = payload.email.strip().lower()
        existing = await AuthService.get_by_email(db, normalized_email)
        if existing:
            raise ValueError(f"User with email '{normalized_email}' already exists.")

        # Validate role
        valid_roles = {r.value for r in UserRole}
        assigned_role = payload.role.strip().upper()
        if assigned_role not in valid_roles:
            assigned_role = UserRole.EMPLOYEE.value

        user = User(
            email=normalized_email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=assigned_role,
            department=payload.department.strip() or "General",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Registered new user: %s (role: %s, dept: %s)", user.email, user.role, user.department)
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user by email and password."""
        user = await AuthService.get_by_email(db, email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
