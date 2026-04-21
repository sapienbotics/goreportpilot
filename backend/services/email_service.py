"""
Email delivery service — sends branded report emails via the Resend API.
Use send_report_email() from async endpoints.
"""
import base64
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _b64_encode_file(path: str) -> str:
    """Read a file from disk and return its base-64 encoded content."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


# ---------------------------------------------------------------------------
# send_report_email
# ---------------------------------------------------------------------------

async def send_report_email(
    *,
    to_emails: list[str],
    subject: str,
    html_body: str,
    sender_name: str = "ReportPilot",
    reply_to: Optional[str] = None,
    pptx_path: Optional[str] = None,
    pdf_path: Optional[str] = None,
    pptx_bytes: Optional[bytes] = None,
    pdf_bytes: Optional[bytes] = None,
) -> dict:
    """
    Send a report email via the Resend API.

    Args:
        to_emails:    List of recipient email addresses.
        subject:      Email subject line.
        html_body:    Full HTML content of the email body.
        sender_name:  Display name shown as the sender (e.g. "Acme Agency").
        reply_to:     Optional reply-to email address.
        pptx_path:    Local path to the .pptx file to attach (optional).
        pdf_path:     Local path to the .pdf file to attach (optional).
        pptx_bytes:   Raw PPTX bytes to attach (takes priority over pptx_path).
        pdf_bytes:    Raw PDF bytes to attach (takes priority over pdf_path).

    Returns:
        Resend API response dict (contains ``id`` on success).

    Raises:
        ValueError: if RESEND_API_KEY is not set.
        httpx.HTTPStatusError: if Resend returns a non-2xx status.
    """
    if not settings.RESEND_API_KEY:
        raise ValueError(
            "RESEND_API_KEY is not configured — "
            "set it in backend/.env to enable email delivery."
        )

    from_address = f"{sender_name} <reports@{settings.EMAIL_FROM_DOMAIN}>"

    attachments: list[dict] = []

    # PPTX — bytes take priority over path
    pptx_content: Optional[str] = None
    if pptx_bytes:
        pptx_content = base64.b64encode(pptx_bytes).decode("ascii")
    elif pptx_path:
        try:
            pptx_content = _b64_encode_file(pptx_path)
        except OSError as exc:
            logger.warning("Could not attach PPTX (%s): %s", pptx_path, exc)
    if pptx_content:
        attachments.append({
            "filename": "report.pptx",
            "content":  pptx_content,
            "type":     "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        })

    # PDF — bytes take priority over path
    pdf_content: Optional[str] = None
    if pdf_bytes:
        pdf_content = base64.b64encode(pdf_bytes).decode("ascii")
    elif pdf_path:
        try:
            pdf_content = _b64_encode_file(pdf_path)
        except OSError as exc:
            logger.warning("Could not attach PDF (%s): %s", pdf_path, exc)
    if pdf_content:
        attachments.append({
            "filename": "report.pdf",
            "content":  pdf_content,
            "type":     "application/pdf",
        })

    payload: dict = {
        "from":    from_address,
        "to":      to_emails,
        "subject": subject,
        "html":    html_body,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if attachments:
        payload["attachments"] = attachments

    logger.info(
        "Sending report email via Resend to %s (subject: %s)",
        to_emails,
        subject,
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        result = response.json()

    logger.info("Report email sent successfully. Resend ID: %s", result.get("id"))
    return result


# ---------------------------------------------------------------------------
# build_report_email_html
# ---------------------------------------------------------------------------

def build_report_email_html(
    *,
    client_name: str,
    period_start: str,
    period_end: str,
    report_title: str,
    executive_summary: str,
    agency_name: str = "Your Agency",
    agency_email: str = "",
    email_footer: str = "",
) -> str:
    """
    Build a branded HTML email body for report delivery.

    Design follows the ReportPilot brand:
    - Indigo header (#4338CA)
    - Executive Summary snippet in the body (max 3 paragraphs)
    - "Full report attached" callout box
    - Clean footer with agency info
    """
    # Build summary paragraphs — handle multi-line string from AI
    summary_paragraphs = [
        line.strip() for line in executive_summary.splitlines() if line.strip()
    ]
    summary_html = "".join(
        f'<p style="margin:0 0 10px 0;color:#334155;font-size:14px;line-height:1.6;">'
        f"{paragraph}</p>"
        for paragraph in summary_paragraphs[:3]   # cap at 3 paragraphs in email
    )
    if not summary_html:
        summary_html = (
            '<p style="color:#64748B;font-size:14px;">'
            "Please see the attached report for full details.</p>"
        )

    footer_text = email_footer or f"Sent by {agency_name} via ReportPilot"
    agency_email_html = (
        f'<p style="margin:4px 0 0 0;font-size:11px;color:#94A3B8;">'
        f'<a href="mailto:{agency_email}" style="color:#94A3B8;text-decoration:none;">'
        f"{agency_email}</a></p>"
        if agency_email
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{report_title}</title>
</head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:Inter,Segoe UI,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation"
         style="background:#F8FAFC;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0" role="presentation"
               style="background:#ffffff;border-radius:12px;overflow:hidden;
                      box-shadow:0 1px 3px rgba(0,0,0,0.08);max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:#4338CA;padding:28px 32px;">
              <p style="margin:0;color:#C7D2FE;font-size:11px;font-weight:700;
                        letter-spacing:0.08em;text-transform:uppercase;">
                {agency_name}
              </p>
              <h1 style="margin:8px 0 0 0;color:#ffffff;font-size:22px;
                         font-weight:700;line-height:1.3;">
                {report_title}
              </h1>
              <p style="margin:8px 0 0 0;color:#A5B4FC;font-size:13px;">
                {period_start} &rarr; {period_end}
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:28px 32px;">
              <p style="margin:0 0 6px 0;color:#64748B;font-size:11px;font-weight:700;
                        text-transform:uppercase;letter-spacing:0.06em;">
                Executive Summary
              </p>
              {summary_html}

              <!-- Attachment callout box -->
              <div style="margin-top:24px;padding:16px 20px;background:#EEF2FF;
                          border-radius:8px;border-left:3px solid #4338CA;">
                <p style="margin:0;font-size:13px;color:#4338CA;font-weight:700;">
                  &#128206; Full report attached
                </p>
                <p style="margin:6px 0 0 0;font-size:13px;color:#334155;line-height:1.5;">
                  The complete performance report is attached. Open it for charts,
                  KPI breakdowns, and detailed strategic recommendations.
                </p>
              </div>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:16px 32px 24px;border-top:1px solid #F1F5F9;">
              <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.5;">
                {footer_text}
              </p>
              {agency_email_html}
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ---------------------------------------------------------------------------
# build_goal_alert_email_html (Phase 6)
# ---------------------------------------------------------------------------

def _format_metric_value(value: float | None, metric_label: str) -> str:
    """Render a metric value with unit hints inferred from the label."""
    if value is None:
        return "\u2014"  # em-dash
    label_lc = (metric_label or "").lower()
    if "rate" in label_lc or "ctr" in label_lc:
        return f"{value:.1f}%"
    if "roas" in label_lc:
        return f"{value:.2f}x"
    if "spend" in label_lc or "cost" in label_lc or "revenue" in label_lc or "cpa" in label_lc:
        return f"{value:,.2f}"
    return f"{value:,.0f}"


def build_goal_alert_email_html(
    *,
    client_name: str,
    metric_label: str,
    actual: float | None,
    target: float,
    comparison: str,
    status: str,           # 'missed' | 'at_risk' | 'on_track'
    period_key: str,
) -> str:
    """
    Phase 6 — alert email. Colour + headline vary with status so agencies
    can triage in the inbox without opening the mail.
    """
    theme = {
        "missed":   {"accent": "#DC2626", "badge_bg": "#FEF2F2", "badge_fg": "#991B1B",
                     "title":  "Goal missed", "icon": "&#9888;"},
        "at_risk":  {"accent": "#D97706", "badge_bg": "#FFFBEB", "badge_fg": "#92400E",
                     "title":  "Goal at risk", "icon": "&#9888;"},
        "on_track": {"accent": "#059669", "badge_bg": "#ECFDF5", "badge_fg": "#065F46",
                     "title":  "Goal on track", "icon": "&#10003;"},
    }.get(status, {
        "accent": "#4338CA", "badge_bg": "#EEF2FF", "badge_fg": "#3730A3",
        "title":  "Goal update", "icon": "&#8226;",
    })

    actual_str = _format_metric_value(actual, metric_label)
    target_str = _format_metric_value(target, metric_label)
    cmp_symbol = {"gte": "&ge;", "lte": "&le;", "eq": "="}.get(comparison, comparison)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>{theme['title']}</title></head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:Inter,Segoe UI,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="background:#F8FAFC;">
    <tr><td align="center" style="padding:32px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" role="presentation"
             style="background:#ffffff;border-radius:12px;overflow:hidden;
                    box-shadow:0 1px 3px rgba(0,0,0,0.08);max-width:600px;width:100%;">
        <tr><td style="background:{theme['accent']};padding:24px 32px;">
          <p style="margin:0;color:#ffffff;font-size:11px;font-weight:700;
                    letter-spacing:0.08em;text-transform:uppercase;opacity:0.9;">
            {client_name}
          </p>
          <h1 style="margin:6px 0 0 0;color:#ffffff;font-size:22px;font-weight:700;line-height:1.3;">
            {theme['icon']} {theme['title']}: {metric_label}
          </h1>
          <p style="margin:6px 0 0 0;color:#ffffff;font-size:13px;opacity:0.9;">
            Period {period_key}
          </p>
        </td></tr>
        <tr><td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0" role="presentation" style="margin-bottom:20px;">
            <tr>
              <td style="width:48%;padding:16px;background:#F8FAFC;border-radius:8px;vertical-align:top;">
                <p style="margin:0;color:#64748B;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">Current</p>
                <p style="margin:6px 0 0 0;color:#0F172A;font-size:24px;font-weight:700;">{actual_str}</p>
              </td>
              <td style="width:4%;"></td>
              <td style="width:48%;padding:16px;background:{theme['badge_bg']};border-radius:8px;vertical-align:top;">
                <p style="margin:0;color:{theme['badge_fg']};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;">Target ({cmp_symbol})</p>
                <p style="margin:6px 0 0 0;color:{theme['badge_fg']};font-size:24px;font-weight:700;">{target_str}</p>
              </td>
            </tr>
          </table>
          <p style="margin:0;color:#334155;font-size:14px;line-height:1.6;">
            This is an automated alert from GoReportPilot. Review the goal in
            your client dashboard to adjust the target or mute alerts if the
            expectation has changed.
          </p>
        </td></tr>
        <tr><td style="padding:16px 32px 24px;border-top:1px solid #F1F5F9;">
          <p style="margin:0;font-size:11px;color:#94A3B8;line-height:1.5;">
            Sent by GoReportPilot. One alert per goal per period.
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
