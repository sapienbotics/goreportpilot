"""
AES-256-GCM encryption/decryption for OAuth tokens.
All platform tokens (GA4, Meta, Google Ads) must be encrypted before storage.
See docs/reportpilot-auth-integration-deepdive.md for security architecture.
IMPORTANT: Never log tokens or encryption keys.
"""
