"""User and Role authentication models with RBAC and department isolation."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import uuid

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid_str() -> str:
    """Generate string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    """Enterprise Role-Based Access Control levels."""
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"
    VIEWER = "VIEWER"


class User(Base):
    """User account entity for enterprise authentication and authorization."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique UUID user identifier",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address used for login",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Secure bcrypt hashed password",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User full display name",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.EMPLOYEE.value,
        index=True,
        doc="RBAC role: ADMIN, MANAGER, EMPLOYEE, VIEWER",
    )
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
        index=True,
        doc="Primary department for document access isolation",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Account active status",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        doc="Account creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
        doc="Last account update timestamp",
    )

    def is_admin(self) -> bool:
        """Check if user has administrator privileges."""
        return self.role == UserRole.ADMIN.value

    def can_manage_department(self, dept: str) -> bool:
        """Check if user can manage the given department."""
        if self.is_admin():
            return True
        return self.role == UserRole.MANAGER.value and self.department.lower() == dept.lower()

    def can_access_document(
        self,
        doc_or_department: Any,
        doc_visibility: str = "organization",
        allowed_roles: Optional[Any] = None,
        allowed_users: Optional[Any] = None,
    ) -> bool:
        """Check if user has permission to retrieve/view this document under RBAC rules."""
        if self.is_admin():
            return True

        if hasattr(doc_or_department, "department"):
            doc_department = getattr(doc_or_department, "department", "General") or "General"
            doc_visibility = getattr(doc_or_department, "visibility", "organization") or "organization"
            allowed_roles = getattr(doc_or_department, "allowed_roles", None)
            allowed_users = getattr(doc_or_department, "allowed_users", None)
        else:
            doc_department = str(doc_or_department)

        # Normalize visibility strings
        vis = str(doc_visibility).lower().strip()
        if vis in ["organization", "public"]:
            return True

        if vis in ["department", "internal"]:
            return self.department.lower() == doc_department.lower()

        if vis in ["restricted", "confidential"]:
            # Check users
            if allowed_users:
                user_list = [u.strip().lower() for u in (allowed_users if isinstance(allowed_users, list) else allowed_users.split(",")) if u.strip()]
                if self.id and self.id.lower() in user_list:
                    return True
            # Check roles
            if allowed_roles:
                role_list = [r.strip().upper() for r in (allowed_roles if isinstance(allowed_roles, list) else allowed_roles.split(",")) if r.strip()]
                if self.role and self.role.upper() in role_list:
                    return True
            return False

        return True
