"""
Razorpay integration service.
Handles customer creation, subscription management, and webhook verification.
"""
import hashlib
import hmac
import logging

from config import settings

logger = logging.getLogger(__name__)


def _get_client():
    """Return a Razorpay client, or None if keys are not configured."""
    key_id = getattr(settings, "RAZORPAY_KEY_ID", "") or ""
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "") or ""
    if not key_id or not key_secret:
        logger.warning("Razorpay keys not configured")
        return None
    try:
        import razorpay  # noqa: PLC0415
        return razorpay.Client(auth=(key_id, key_secret))
    except ImportError:
        logger.error("razorpay package not installed — run: pip install razorpay")
        return None


def create_customer(email: str, name: str) -> dict | None:
    """Create a Razorpay customer."""
    client = _get_client()
    if not client:
        return None
    try:
        return client.customer.create({"name": name, "email": email})
    except Exception as exc:
        logger.error("Failed to create Razorpay customer: %s", exc)
        return None


def create_subscription(
    plan_id: str, customer_id: str, total_count: int = 120
) -> dict | None:
    """Create a Razorpay subscription for a customer."""
    client = _get_client()
    if not client:
        return None
    try:
        return client.subscription.create(
            {
                "plan_id": plan_id,
                "customer_id": customer_id,
                "total_count": total_count,
                "customer_notify": 1,
            }
        )
    except Exception as exc:
        logger.error("Failed to create Razorpay subscription: %s", exc)
        return None


def cancel_subscription(subscription_id: str, cancel_at_end: bool = True) -> dict | None:
    """Cancel a Razorpay subscription."""
    client = _get_client()
    if not client:
        return None
    try:
        return client.subscription.cancel(
            subscription_id,
            {"cancel_at_cycle_end": 1 if cancel_at_end else 0},
        )
    except Exception as exc:
        logger.error("Failed to cancel Razorpay subscription: %s", exc)
        return None


def fetch_subscription(subscription_id: str) -> dict | None:
    """Fetch subscription details from Razorpay."""
    client = _get_client()
    if not client:
        return None
    try:
        return client.subscription.fetch(subscription_id)
    except Exception as exc:
        logger.error("Failed to fetch subscription: %s", exc)
        return None


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Razorpay webhook signature."""
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "") or ""
    if not secret:
        logger.warning("Razorpay webhook secret not configured")
        return False
    try:
        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        logger.error("Webhook verification failed: %s", exc)
        return False


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay payment signature for checkout."""
    client = _get_client()
    if not client:
        return False
    try:
        import razorpay  # noqa: PLC0415
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            }
        )
        return True
    except Exception:
        return False
