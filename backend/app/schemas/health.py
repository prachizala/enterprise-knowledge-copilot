"""Schemas for root and health check endpoints."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    """Schema for root GET / endpoint."""
    message: str = Field(..., examples=["Enterprise Knowledge Copilot API"])
    status: str = Field(..., examples=["running"])


class ServiceStatus(BaseModel):
    """Schema for individual subsystem readiness state."""
    name: str
    status: str
    configured: bool
    details: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema for GET /api/health endpoint."""
    status: str = Field(default="healthy", examples=["healthy"])
    app_name: str
    version: str
    environment: str
    services: Dict[str, ServiceStatus]
