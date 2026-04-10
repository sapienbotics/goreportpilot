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
    report_config: dict | None = None  # Per-client report customisation (sections, KPIs, template)
    report_language: str | None = None  # BCP-47 language code, e.g. "en", "fr", "de"

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
    report_config: dict | None = None  # Per-client section toggles, KPI selection, template
    report_language: str | None = None  # BCP-47 language code, e.g. "en", "fr", "de"
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
    template: str = "full"  # "full" | "summary" | "brief"
    visual_template: str = "modern_clean"  # "modern_clean" | "dark_executive" | "colorful_agency"
    csv_sources: list[dict] | None = None  # ad-hoc CSV data for this report only


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
    meta_currency: str = "USD"   # Billing currency of the connected Meta ad account
    user_edits: dict | None = None  # Manual text overrides; keys match narrative keys
    pptx_url: str | None = None
    pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Report update / editing schemas
# ---------------------------------------------------------------------------

class ReportUpdateRequest(BaseModel):
    """PATCH /api/reports/{id} — save manual text edits for one or more narrative sections."""
    user_edits: dict[str, str]  # e.g. {"executive_summary": "edited text …"}


class ReportSectionRegenerateRequest(BaseModel):
    """POST /api/reports/{id}/regenerate-section — re-run AI for a single section."""
    section: str    # One of: executive_summary | website_performance | paid_advertising |
                    #          key_wins | concerns | next_steps


class ReportSendRequest(BaseModel):
    """POST /api/reports/{id}/send — deliver report by email."""
    to_emails: list[str]          # Recipient email addresses
    subject: str | None = None    # Override default subject line
    attachment: str = "both"      # "pdf" | "pptx" | "both"
    sender_name: str | None = None   # Override agency/sender display name
    reply_to: str | None = None      # Override reply-to address


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

# ---------------------------------------------------------------------------
# Meta OAuth schemas
# ---------------------------------------------------------------------------

class MetaAuthUrlResponse(BaseModel):
    """Returned by GET /api/auth/meta/url"""
    url: str
    state: str


class MetaAdAccount(BaseModel):
    """A single Meta ad account returned by the callback endpoint."""
    account_id: str   # e.g. "act_123456789"
    account_name: str
    currency: str
    status: int       # 1 = active, others indicate paused/disabled


class MetaCallbackRequest(BaseModel):
    """Frontend sends this after receiving the Meta OAuth redirect."""
    code: str


class MetaCallbackResponse(BaseModel):
    """Backend exchanges code for tokens and returns available ad accounts."""
    ad_accounts: list[MetaAdAccount]
    token_handle: str
    expires_in: int


class ConnectionCreate(BaseModel):
    client_id: str
    platform: str          # "google_analytics" | "meta_ads" | "google_ads"
    account_id: str        # GA4 property_id or Meta ad_account_id
    account_name: str
    # Opaque encrypted token handle returned by GoogleCallbackResponse.
    # Backend will parse and store this securely.
    token_handle: str
    currency: str = "USD"  # Ad account billing currency (e.g. "INR", "USD")


class ConnectionResponse(BaseModel):
    id: str
    client_id: str
    platform: str
    account_id: str
    account_name: str
    status: str             # "active" | "expired" | "error"
    currency: str = "USD"
    token_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectionListResponse(BaseModel):
    connections: list[ConnectionResponse]
    total: int


# ---------------------------------------------------------------------------
# Settings / Profile schemas
# ---------------------------------------------------------------------------

class ProfileUpdate(BaseModel):
    """PATCH /api/settings/profile — update any subset of agency profile fields."""
    agency_name: str | None = None
    agency_email: str | None = None
    agency_website: str | None = None
    sender_name: str | None = None
    reply_to_email: str | None = None
    email_footer: str | None = None
    brand_color: str | None = None        # hex string e.g. "#4338CA"
    timezone: str | None = None
    default_ai_tone: str | None = None
    notification_report_generated: bool | None = None
    notification_connection_expired: bool | None = None
    notification_payment_failed: bool | None = None


# ---------------------------------------------------------------------------
# Scheduled report schemas
# ---------------------------------------------------------------------------

class ScheduledReportCreate(BaseModel):
    client_id: str
    frequency: str                  # "weekly" | "biweekly" | "monthly"
    day_of_week: int | None = None  # 0=Monday … 6=Sunday (weekly/biweekly)
    day_of_month: int | None = None # 1-28 (monthly)
    time_utc: str = "09:00"         # "HH:MM"
    template: str = "full"          # "full" | "summary" | "brief"
    auto_send: bool = False
    send_to_emails: list[str] = []
    # Attachment format for the delivered email: "pdf" | "pptx" | "both".
    attachment_type: str = "both"
    # Visual template applied when rendering the report. Clamped to the
    # user's plan-allowed list inside _generate_report_internal, so any
    # invalid value here is silently overridden at run time.
    visual_template: str = "modern_clean"


class ScheduledReportUpdate(BaseModel):
    frequency: str | None = None
    day_of_week: int | None = None
    day_of_month: int | None = None
    time_utc: str | None = None
    template: str | None = None
    auto_send: bool | None = None
    send_to_emails: list[str] | None = None
    is_active: bool | None = None
    attachment_type: str | None = None
    visual_template: str | None = None


class ScheduledReportResponse(BaseModel):
    id: str
    client_id: str
    user_id: str
    frequency: str
    day_of_week: int | None = None
    day_of_month: int | None = None
    time_utc: str
    template: str
    auto_send: bool
    send_to_emails: list[str]
    is_active: bool
    attachment_type: str = "both"
    visual_template: str = "modern_clean"
    last_generated_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
