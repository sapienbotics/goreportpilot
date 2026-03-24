"""
CSV parser for custom KPI data uploads.
Supports metric_name / current_value / previous_value / unit columns.
"""
import csv
import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"metric_name", "current_value"}
OPTIONAL_COLUMNS = {"previous_value", "unit"}
MAX_METRICS = 20

# Currency and formatting symbols to strip before parsing numbers
_STRIP_PATTERN = re.compile(r"[\$₹€£¥,\s%]")


def _parse_number(val: str) -> Optional[float]:
    """
    Convert a raw string value to float.

    Strips currency symbols ($, ₹, €, £, ¥), commas, whitespace, and
    percent signs before conversion. Returns None if the string is empty
    or cannot be parsed.
    """
    if not val or not val.strip():
        return None
    cleaned = _STRIP_PATTERN.sub("", val.strip())
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        logger.warning("Could not parse numeric value: %r", val)
        return None


def _clean_source_name(filename: str) -> str:
    """
    Derive a human-readable source name from a filename.

    Removes the .csv extension, replaces underscores and hyphens with
    spaces, and applies title case. Example: 'linkedin_ads.csv' → 'Linkedin Ads'.
    """
    name = filename
    if name.lower().endswith(".csv"):
        name = name[:-4]
    name = name.replace("_", " ").replace("-", " ")
    return name.title()


def parse_kpi_csv(file_content: bytes, filename: str) -> dict:
    """
    Parse a CSV file containing KPI metrics.

    Required columns (case-insensitive):
        metric_name     — display name for the metric
        current_value   — numeric value for the current period

    Optional columns:
        previous_value  — numeric value for the previous period;
                          used to calculate change percentage
        unit            — display unit string (e.g. '%', '$', 'sessions')

    Processing rules:
    - Strips currency symbols and formatting characters from numeric fields.
    - Calculates change percentage when both current and previous values
      are present and previous_value != 0.
    - Caps output at MAX_METRICS (20) rows after skipping invalid rows.
    - Attempts UTF-8 decoding first, falls back to latin-1.

    Returns:
        {
            "source_name": str,
            "metrics": [
                {
                    "name": str,
                    "current_value": float,
                    "previous_value": float | None,
                    "unit": str,
                    "change": float | None,   # percentage, e.g. 12.5 means +12.5%
                }
            ]
        }

    Raises:
        ValueError: if required columns are missing or the file cannot be parsed.
    """
    # --- Decode ---
    text: str
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Could not decode the CSV file. Please save it as UTF-8 or Latin-1."
            ) from exc

    # --- Parse CSV ---
    try:
        reader = csv.DictReader(io.StringIO(text))
        if reader.fieldnames is None:
            raise ValueError("The CSV file appears to be empty or has no header row.")
        raw_rows = list(reader)
    except csv.Error as exc:
        raise ValueError(f"Failed to parse CSV: {exc}") from exc

    # --- Normalise column names (strip whitespace, lowercase) ---
    fieldnames_normalised = {
        name.strip().lower(): name for name in (reader.fieldnames or [])
    }

    missing = REQUIRED_COLUMNS - set(fieldnames_normalised.keys())
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(sorted(missing))}. "
            f"Required columns are: metric_name, current_value."
        )

    has_previous = "previous_value" in fieldnames_normalised
    has_unit = "unit" in fieldnames_normalised

    # Map normalised key → original header for DictReader row access
    col_metric = fieldnames_normalised["metric_name"]
    col_current = fieldnames_normalised["current_value"]
    col_previous = fieldnames_normalised.get("previous_value")
    col_unit = fieldnames_normalised.get("unit")

    metrics: list[dict] = []

    for row_index, row in enumerate(raw_rows, start=2):  # row 1 is header
        if len(metrics) >= MAX_METRICS:
            logger.info(
                "CSV row limit reached (%d). Remaining rows ignored.", MAX_METRICS
            )
            break

        raw_name = (row.get(col_metric) or "").strip()
        raw_current = row.get(col_current) or ""

        if not raw_name:
            logger.debug("Row %d skipped: empty metric_name.", row_index)
            continue

        current_value = _parse_number(raw_current)
        if current_value is None:
            logger.warning(
                "Row %d skipped: could not parse current_value %r for metric %r.",
                row_index,
                raw_current,
                raw_name,
            )
            continue

        previous_value: Optional[float] = None
        if has_previous and col_previous:
            previous_value = _parse_number(row.get(col_previous) or "")

        unit = ""
        if has_unit and col_unit:
            unit = (row.get(col_unit) or "").strip()

        change: Optional[float] = None
        if previous_value is not None and previous_value != 0:
            change = round(
                ((current_value - previous_value) / abs(previous_value)) * 100, 2
            )

        metrics.append(
            {
                "name": raw_name,
                "current_value": current_value,
                "previous_value": previous_value,
                "unit": unit,
                "change": change,
            }
        )

    if not metrics:
        raise ValueError(
            "No valid metric rows found in the CSV. "
            "Ensure metric_name is non-empty and current_value is a valid number."
        )

    source_name = _clean_source_name(filename)

    return {"source_name": source_name, "metrics": metrics}


# ---------------------------------------------------------------------------
# Template generator
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, str] = {
    "linkedin_ads": (
        "metric_name,current_value,previous_value,unit\n"
        "Impressions,45200,38900,\n"
        "Clicks,1340,1100,\n"
        "Click-Through Rate,2.96,2.83,%\n"
        "Spend,1850.00,1600.00,$\n"
        "Cost Per Click,1.38,1.45,$\n"
        "Leads Generated,87,71,\n"
        "Cost Per Lead,21.26,22.54,$\n"
        "Engagement Rate,3.5,3.1,%\n"
        "Follower Growth,210,180,\n"
        "Video Views,8900,7200,\n"
    ),
    "tiktok_ads": (
        "metric_name,current_value,previous_value,unit\n"
        "Impressions,320000,275000,\n"
        "Clicks,9800,8100,\n"
        "Click-Through Rate,3.06,2.95,%\n"
        "Spend,2400.00,2100.00,$\n"
        "Cost Per Click,0.24,0.26,$\n"
        "Video Views,185000,160000,\n"
        "Video Completion Rate,42.5,39.8,%\n"
        "Conversions,310,265,\n"
        "Cost Per Conversion,7.74,7.92,$\n"
        "Return on Ad Spend,3.8,3.5,\n"
    ),
    "mailchimp": (
        "metric_name,current_value,previous_value,unit\n"
        "Emails Sent,12500,11800,\n"
        "Open Rate,28.4,26.1,%\n"
        "Click Rate,4.7,4.2,%\n"
        "Unsubscribe Rate,0.3,0.4,%\n"
        "Bounce Rate,1.2,1.5,%\n"
        "Revenue Attributed,3200.00,2750.00,$\n"
        "New Subscribers,340,290,\n"
        "List Size,18450,18110,\n"
        "Spam Complaints,2,4,\n"
        "Automation Emails Sent,4200,3900,\n"
    ),
    "shopify": (
        "metric_name,current_value,previous_value,unit\n"
        "Total Revenue,28500.00,24200.00,$\n"
        "Orders,620,540,\n"
        "Average Order Value,45.97,44.81,$\n"
        "Conversion Rate,3.2,2.9,%\n"
        "Sessions,19375,18621,\n"
        "Returning Customer Rate,38.5,35.2,%\n"
        "Cart Abandonment Rate,68.1,70.4,%\n"
        "Refund Rate,2.1,2.6,%\n"
        "Units Sold,1450,1260,\n"
        "Top Product Revenue,5400.00,4100.00,$\n"
    ),
    "generic": (
        "metric_name,current_value,previous_value,unit\n"
        "Metric One,1000,900,\n"
        "Metric Two,55.5,50.0,%\n"
        "Metric Three,7800.00,6500.00,$\n"
        "Metric Four,320,280,\n"
        "Metric Five,4.8,4.2,\n"
    ),
}


def generate_template_csv(source_type: str) -> str:
    """
    Return a CSV template string for the given source type.

    Supported source_type values:
        linkedin_ads, tiktok_ads, mailchimp, shopify, generic

    Falls back to the generic template for unrecognised types.
    """
    key = source_type.lower().replace(" ", "_").replace("-", "_")
    template = _TEMPLATES.get(key, _TEMPLATES["generic"])
    logger.info("Generated CSV template for source type: %r", source_type)
    return template
