"""Authentication and authorization package."""

from app.auth.security import create_access_token, decode_access_token, hash_password, verify_password
from app.auth.schemas import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.auth.service import AuthService
from app.auth.dependencies import (
    build_accessible_documents_filter,
    check_document_access,
    get_current_user,
    require_authenticated_user,
    require_role,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "UserResponse",
    "AuthService",
    "get_current_user",
    "require_authenticated_user",
    "require_role",
    "check_document_access",
    "build_accessible_documents_filter",
]
