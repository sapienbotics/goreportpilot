"""
OAuth callback routes for GA4, Meta, and Google Ads.
Handles token exchange and storage after OAuth redirect.
See docs/reportpilot-auth-integration-deepdive.md for full specification.
"""
from fastapi import APIRouter

router = APIRouter()
