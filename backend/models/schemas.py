"""
Pydantic v2 request/response models for all API endpoints.
See docs/reportpilot-feature-design-blueprint.md for database schema and field definitions.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Client schemas
# ---------------------------------------------------------------------------

class ClientCreate(BaseModel):
    name: str
    website_url: str | None = None
    industry: str | None = None
    primary_contact_email: str | None = None
    goals_context: str | None = None
    ai_tone: str = "professional"
    notes: str | None = None

    @field_validator("ai_tone")
    @classmethod
    def validate_ai_tone(cls, v: str) -> str:
        allowed = {"professional", "friendly", "technical", "executive"}
        if v not in allowed:
            raise ValueError(f"ai_tone must be one of {allowed}")
        return v


class ClientUpdate(BaseModel):
    name: str | None = None
    website_url: str | None = None
    industry: str | None = None
    primary_contact_email: str | None = None
    goals_context: str | None = None
    ai_tone: str | None = None
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("ai_tone")
    @classmethod
    def validate_ai_tone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"professional", "friendly", "technical", "executive"}
        if v not in allowed:
            raise ValueError(f"ai_tone must be one of {allowed}")
        return v


class ClientResponse(BaseModel):
    id: str
    user_id: str
    name: str
    website_url: str | None = None
    industry: str | None = None
    primary_contact_email: str | None = None
    logo_url: str | None = None
    goals_context: str | None = None
    ai_tone: str
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    clients: list[ClientResponse]
    total: int
