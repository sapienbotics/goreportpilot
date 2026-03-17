"""
Stripe and email delivery webhooks.
Handles Stripe subscription events and Resend delivery confirmations.
See docs/reportpilot-feature-design-blueprint.md for full specification.
"""
from fastapi import APIRouter

router = APIRouter()
