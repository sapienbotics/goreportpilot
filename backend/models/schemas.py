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


# ---------------------------------------------------------------------------
# Report schemas
# ---------------------------------------------------------------------------

class ReportGenerateRequest(BaseModel):
    client_id: str
    period_start: str  # "YYYY-MM-DD"
    period_end: str    # "YYYY-MM-DD"


class ReportResponse(BaseModel):
    id: str
    user_id: str
    client_id: str
    client_name: str | None = None
    title: str
    status: str
    period_start: str
    period_end: str
    narrative: dict | None = None
    data_summary: dict | None = None
    pptx_url: str | None = None
    pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: str
    user_id: str
    client_id: str
    client_name: str | None = None
    title: str
    status: str
    period_start: str
    period_end: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportListItem]
    total: int


# ---------------------------------------------------------------------------
# Auth / OAuth schemas
# ---------------------------------------------------------------------------

class GoogleAuthUrlResponse(BaseModel):
    """Returned by GET /api/auth/google/url"""
    url: str
    state: str


class Ga4Property(BaseModel):
    """A single GA4 property from the Google Analytics Admin API"""
    property_id: str   # e.g. "properties/123456789"
    display_name: str
    time_zone: str | None = None
    currency_code: str | None = None


class GoogleCallbackRequest(BaseModel):
    """Frontend sends this after receiving the OAuth redirect."""
    code: str
    state: str


class GoogleCallbackResponse(BaseModel):
    """Backend exchanges code for tokens and returns available GA4 properties."""
    properties: list[Ga4Property]
    # Opaque handle the frontend sends back when creating a connection.
    # Contains the encrypted tokens — never expose the raw tokens to the frontend.
    token_handle: str


# ---------------------------------------------------------------------------
# Connection schemas
# ---------------------------------------------------------------------------

class ConnectionCreate(BaseModel):
    client_id: str
    platform: str          # "google_analytics" | "meta_ads" | "google_ads"
    account_id: str        # GA4 property_id or Meta ad_account_id
    account_name: str
    # Opaque encrypted token handle returned by GoogleCallbackResponse.
    # Backend will parse and store this securely.
    token_handle: str


class ConnectionResponse(BaseModel):
    id: str
    client_id: str
    platform: str
    account_id: str
    account_name: str
    status: str             # "active" | "expired" | "error"
    token_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionResponse]
    total: int
