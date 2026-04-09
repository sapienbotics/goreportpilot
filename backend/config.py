from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to this file so it's found regardless of the
# working directory uvicorn is started from.
_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # Meta OAuth
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_REDIRECT_URI: str = ""

    # Google Ads
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = ""
    GOOGLE_ADS_REDIRECT_URI: str = ""

    # Search Console
    SEARCH_CONSOLE_REDIRECT_URI: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Token encryption
    TOKEN_ENCRYPTION_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""
    STRIPE_PRICE_AGENCY: str = ""

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    # Razorpay plan IDs — create these in Razorpay dashboard, then fill in
    RAZORPAY_PLAN_STARTER_MONTHLY: str = ""
    RAZORPAY_PLAN_STARTER_ANNUAL: str = ""
    RAZORPAY_PLAN_PRO_MONTHLY: str = ""
    RAZORPAY_PLAN_PRO_ANNUAL: str = ""
    RAZORPAY_PLAN_AGENCY_MONTHLY: str = ""
    RAZORPAY_PLAN_AGENCY_ANNUAL: str = ""
    # USD plan IDs — separate Razorpay plans billed in USD
    RAZORPAY_PLAN_STARTER_MONTHLY_USD: str = ""
    RAZORPAY_PLAN_STARTER_ANNUAL_USD: str = ""
    RAZORPAY_PLAN_PRO_MONTHLY_USD: str = ""
    RAZORPAY_PLAN_PRO_ANNUAL_USD: str = ""
    RAZORPAY_PLAN_AGENCY_MONTHLY_USD: str = ""
    RAZORPAY_PLAN_AGENCY_ANNUAL_USD: str = ""

    # Resend
    RESEND_API_KEY: str = ""
    EMAIL_FROM_DOMAIN: str = "reportpilot.co"   # Domain for report delivery emails

    # App
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    def model_post_init(self, __context: object) -> None:
        """Derive redirect URIs from FRONTEND_URL when not explicitly set."""
        _defaults = {
            "GOOGLE_REDIRECT_URI": "/api/auth/callback/google-analytics",
            "META_REDIRECT_URI": "/api/auth/callback/meta-ads",
            "GOOGLE_ADS_REDIRECT_URI": "/api/auth/callback/google-ads",
            "SEARCH_CONSOLE_REDIRECT_URI": "/api/auth/callback/search-console",
        }
        for attr, path in _defaults.items():
            if not getattr(self, attr):
                object.__setattr__(self, attr, f"{self.FRONTEND_URL}{path}")


settings = Settings()
