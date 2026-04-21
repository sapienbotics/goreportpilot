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
    # Design System (Option F v1) — single per-client theme choice.
    # Replaces the old cover_design_preset concept.
    theme: str | None = None
    # Cover text + brand overrides
    cover_headline: str | None = None
    cover_subtitle: str | None = None
    cover_brand_primary_color: str | None = None
    cover_brand_accent_color: str | None = None
    # Logo placement (unchanged from Phase 3)
    cover_agency_logo_position: str | None = None
    cover_agency_logo_size: str | None = None
    cover_client_logo_position: str | None = None
    cover_client_logo_size: str | None = None
    # DEPRECATED — kept nullable for backward compat with old clients.
    # The UI no longer writes these. Migration 017 ignores them. Future
    # migration 018 will drop the columns.
    cover_design_preset: str | None = None
    cover_hero_image_url: str | None = None

    @field_validator("ai_tone")
    @classmethod
    def validate_ai_tone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"professional", "friendly", "technical", "executive"}
        if v not in allowed:
            raise ValueError(f"ai_tone must be one of {allowed}")
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {
            "modern_clean", "dark_executive", "colorful_agency",
            "bold_geometric", "minimal_elegant", "gradient_modern",
        }
        if v not in allowed:
            raise ValueError(f"theme must be one of {allowed}")
        return v

    @field_validator("cover_agency_logo_position", "cover_client_logo_position")
    @classmethod
    def validate_logo_position(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {
            "default", "top-left", "top-right", "top-center",
            "footer-left", "footer-right", "footer-center", "center",
        }
        if v not in allowed:
            raise ValueError(f"logo position must be one of {allowed}")
        return v

    @field_validator("cover_agency_logo_size", "cover_client_logo_size")
    @classmethod
    def validate_logo_size(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {"default", "small", "medium", "large"}
        if v not in allowed:
            raise ValueError(f"logo size must be one of {allowed}")
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
    # Design System (Option F v1)
    theme: str | None = None
    cover_headline: str | None = None
    cover_subtitle: str | None = None
    cover_brand_primary_color: str | None = None
    cover_brand_accent_color: str | None = None
    cover_agency_logo_position: str | None = None
    cover_agency_logo_size: str | None = None
    cover_client_logo_position: str | None = None
    cover_client_logo_size: str | None = None
    # DEPRECATED — see ClientUpdate notes.
    cover_design_preset: str | None = None
    cover_hero_image_url: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    clients: list[ClientResponse]
    total: int


# ---------------------------------------------------------------------------
# Report schemas
# ---------------------------------------------------------------------------

class CoverPreviewRequest(BaseModel):
    """Generate a single-slide PPTX preview of a cover design (Option F v1).

    All fields except `client_id` are optional per-request overrides. When
    omitted, the stored value on `clients` is used.
    """
    client_id: str
    theme: str | None = None
    headline: str | None = None
    subtitle: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    agency_logo_position: str | None = None
    agency_logo_size: str | None = None
    client_logo_position: str | None = None
    client_logo_size: str | None = None

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str | None) -> str | None:
        if v is None:
            return v
        allowed = {
            "modern_clean", "dark_executive", "colorful_agency",
            "bold_geometric", "minimal_elegant", "gradient_modern",
        }
        if v not in allowed:
            raise ValueError(f"theme must be one of {allowed}")
        return v


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
    status: str             # "active" | "expired" | "error" (OAuth callback state)
    currency: str = "USD"
    # Phase 2 — live probe state, independent of `status`
    health_status: str = "healthy"  # "healthy" | "warning" | "broken" | "expiring_soon"
    last_error_message: str | None = None
    last_health_check_at: datetime | None = None
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
    comment_notifications_enabled: bool | None = None  # Phase 5


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


# ---------------------------------------------------------------------------
# Goal schemas (Phase 6)
# ---------------------------------------------------------------------------

_GOAL_COMPARISONS = {"gte", "lte", "eq"}
_GOAL_PERIODS     = {"weekly", "monthly"}


class GoalCreate(BaseModel):
    metric: str
    comparison: str = "gte"
    target_value: float
    tolerance_pct: float = 5.0
    period: str = "monthly"
    is_active: bool = True
    alert_emails: list[str] | None = None

    @field_validator("comparison")
    @classmethod
    def _v_cmp(cls, v: str) -> str:
        if v not in _GOAL_COMPARISONS:
            raise ValueError(f"comparison must be one of {_GOAL_COMPARISONS}")
        return v

    @field_validator("period")
    @classmethod
    def _v_period(cls, v: str) -> str:
        if v not in _GOAL_PERIODS:
            raise ValueError(f"period must be one of {_GOAL_PERIODS}")
        return v


class GoalUpdate(BaseModel):
    metric: str | None = None
    comparison: str | None = None
    target_value: float | None = None
    tolerance_pct: float | None = None
    period: str | None = None
    is_active: bool | None = None
    alert_emails: list[str] | None = None

    @field_validator("comparison")
    @classmethod
    def _v_cmp(cls, v: str | None) -> str | None:
        if v is not None and v not in _GOAL_COMPARISONS:
            raise ValueError(f"comparison must be one of {_GOAL_COMPARISONS}")
        return v

    @field_validator("period")
    @classmethod
    def _v_period(cls, v: str | None) -> str | None:
        if v is not None and v not in _GOAL_PERIODS:
            raise ValueError(f"period must be one of {_GOAL_PERIODS}")
        return v


class GoalResponse(BaseModel):
    id: str
    client_id: str
    user_id: str
    metric: str
    metric_label: str | None = None
    comparison: str
    target_value: float
    tolerance_pct: float
    period: str
    is_active: bool
    alert_emails: list[str] = []
    last_evaluated_at: datetime | None = None
    # Computed fields — populated by the GET endpoint, not stored in DB.
    current_value: float | None = None
    status: str | None = None  # 'on_track' | 'at_risk' | 'missed' | 'no_data'
    period_key: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GoalListResponse(BaseModel):
    goals: list[GoalResponse]
    total: int
    limit: int   # effective limit (accounts for trial override)
    plan: str    # plan name e.g. 'starter', 'pro', 'agency', 'trial'
    is_trial: bool = False
    plan_goal_limit: int | None = None  # what the limit will be AFTER trial ends


# ---------------------------------------------------------------------------
# Business-context AI enhancement (Phase 7 UX)
# ---------------------------------------------------------------------------

class EnhanceContextRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _v_text(cls, v: str) -> str:
        stripped = (v or "").strip()
        if len(stripped) < 20:
            raise ValueError("text must be at least 20 characters")
        if len(stripped) > 2000:
            # Hard ceiling well above the 500-char UI counter — catches abuse
            # without blocking users who paste a long brief and then expect
            # the model to condense it.
            raise ValueError("text exceeds 2000 characters")
        return stripped


class EnhanceContextResponse(BaseModel):
    enhanced: str
