"""API v1 Router aggregation."""

from fastapi import APIRouter
from app.api.v1.documents import router as documents_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(documents_router)

__all__ = ["v1_router"]
