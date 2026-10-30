"""Tests for User authentication and RBAC document access control."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import create_access_token, hash_password, verify_password
from app.models.document import Document
from app.models.user import User, UserRole


def test_password_hashing():
    pwd = "EnterpriseSecurePass123!"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_creation():
    token = create_access_token(
        subject="user-uuid-1",
        role="admin",
        department="Engineering",
    )
    assert token is not None
    assert len(token) > 20


def test_user_can_access_document_logic():
    admin_user = User(
        id="u-admin",
        email="admin@acme.com",
        full_name="Admin User",
        role=UserRole.ADMIN.value,
        department="Engineering",
    )
    eng_user = User(
        id="u-eng",
        email="eng@acme.com",
        full_name="Eng User",
        role=UserRole.EMPLOYEE.value,
        department="Engineering",
    )
    hr_user = User(
        id="u-hr",
        email="hr@acme.com",
        full_name="HR User",
        role=UserRole.EMPLOYEE.value,
        department="HR",
    )

    public_doc = Document(
        id="d-public",
        filename="public.pdf",
        original_filename="public.pdf",
        file_type="pdf",
        department="Engineering",
        visibility="public",
    )
    internal_doc = Document(
        id="d-internal",
        filename="internal.pdf",
        original_filename="internal.pdf",
        file_type="pdf",
        department="Engineering",
        visibility="internal",
    )
    confidential_doc = Document(
        id="d-conf",
        filename="conf.pdf",
        original_filename="conf.pdf",
        file_type="pdf",
        department="Engineering",
        visibility="confidential",
        allowed_roles=["admin", "manager"],
    )

    # Admin accesses everything
    assert admin_user.can_access_document(public_doc) is True
    assert admin_user.can_access_document(internal_doc) is True
    assert admin_user.can_access_document(confidential_doc) is True

    # Eng user accesses internal doc from their department
    assert eng_user.can_access_document(public_doc) is True
    assert eng_user.can_access_document(internal_doc) is True
    # But not confidential
    assert eng_user.can_access_document(confidential_doc) is False

    # HR user accesses public doc, but internal doc is in Engineering
    assert hr_user.can_access_document(public_doc) is True
    assert hr_user.can_access_document(internal_doc) is False


@pytest.mark.asyncio
async def test_auth_routes_flow(async_client: AsyncClient):
    # 1. Register
    reg_payload = {
        "email": "test_dev@acme.com",
        "full_name": "Test Developer",
        "password": "SecurePassword123!",
        "department": "Engineering",
        "role": "EMPLOYEE",
    }
    res = await async_client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 201
    user_data = res.json()
    assert user_data["email"] == "test_dev@acme.com"

    # 2. Login
    login_payload = {
        "email": "test_dev@acme.com",
        "password": "SecurePassword123!",
    }
    login_res = await async_client.post("/api/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    token = token_data["access_token"]
    assert token is not None

    # 3. Access /me
    me_res = await async_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "test_dev@acme.com"
    assert me_data["department"] == "Engineering"
