"""
Production-grade CSV parser for custom KPI data uploads.

Handles:
- Encoding detection  : UTF-8 BOM → UTF-8 → chardet auto-detect → Latin-1 fallback
- Delimiter detection : comma, semicolon, tab, pipe (csv.Sniffer)
- Binary rejection    : Excel (.xlsx/.xls), PDF, JPEG, PNG, GIF with clear instructions
- Flexible columns    : aliases for metric_name, current_value, previous_value, unit
- Number parsing      : K/M/B suffixes, European decimal (1.234,56), currency symbols,
                        space-separated thousands
- Unit auto-detection : from value symbols (%, $, ₹) AND metric/column name keywords
- Filename cleaning   : leading dates, trailing template/export/v2/final/etc stripped
- Comment rows        : lines starting with '#' and wholly blank rows are skipped
- Clear validation    : specific error messages with suggested fixes for every failure mode
"""
import csv
import io
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

MAX_METRICS = 20

# ─── Column name aliases ──────────────────────────────────────────────────────
# Each canonical column maps to a list of accepted aliases (lowercase, underscored).
_COL_ALIASES: dict[str, list[str]] = {
    "metric_name": [
        "metric_name", "metric", "name", "kpi", "indicator",
        "measure", "label", "description", "kpi_name", "metric_label",
        "category", "item",
    ],
    "current_value": [
        "current_value", "current", "value", "actual", "this_period",
        "this_month", "current_period", "amount", "total", "result",
        "current_month", "period_value",
    ],
    "previous_value": [
        "previous_value", "previous", "prev", "last_period", "last_month",
        "prior", "prior_period", "compare", "comparison", "baseline",
        "previous_month", "last",
    ],
    "unit": [
        "unit", "type", "format", "metric_type", "unit_type",
        "data_type", "measurement", "scale",
    ],
}

# ─── Metric/column name → unit hint (auto-detect when no unit column) ─────────
_NAME_UNIT_HINTS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bspend\b|\bcost\b|\brevenue\b|\bbudget\b|\bprice\b|\bcpc\b|\bcpm\b|\bcpa\b|\bsales\b|\bearnings\b", re.I), "currency"),
    (re.compile(r"\brate\b|\bratio\b|\bctr\b|\bpercentage\b|\bpct\b|\bcompletion\b|\bopen rate\b|\bclick rate\b|\bbounce\b|\bengagement\b|\bconversion rate\b", re.I), "percent"),
]

# ─── Unit alias normalisation map ────────────────────────────────────────────
_UNIT_ALIASES: dict[str, str] = {
    # Symbols
    "%": "percent",
    "$": "currency", "₹": "currency", "€": "currency",
    "£": "currency", "¥": "currency",
    # Short names
    "rs": "currency", "rs.": "currency",
    "inr": "currency", "usd": "currency", "eur": "currency",
    "gbp": "currency", "jpy": "currency",
    # Explicit semantic names
    "currency": "currency", "money": "currency", "price": "currency",
    "amount": "currency", "cost": "currency",
    "percent": "percent", "percentage": "percent", "pct": "percent",
    "rate": "percent", "ratio": "percent",
    "number": "number", "count": "number", "num": "number",
    "integer": "number", "int": "number", "quantity": "number",
    "sessions": "number", "clicks": "number", "impressions": "number",
    "views": "number", "visits": "number",
}

# ─── Binary file magic byte signatures ───────────────────────────────────────
_BINARY_SIGNATURES: list[tuple[bytes, str]] = [
    (
        b"PK\x03\x04",
        "This looks like an Excel file (.xlsx). "
        "Please open it in Excel/Sheets and use File → Download → CSV to export as CSV.",
    ),
    (
        b"\xd0\xcf\x11\xe0",
        "This looks like an older Excel file (.xls). "
        "Please open it in Excel and save as CSV (comma-separated values).",
    ),
    (
        b"%PDF",
        "This is a PDF file. "
        "Please convert your data to a CSV spreadsheet first.",
    ),
    (
        b"\xff\xd8\xff",
        "This is a JPEG image, not a CSV. "
        "Please upload a CSV file with your metrics data.",
    ),
    (
        b"\x89PNG",
        "This is a PNG image, not a CSV. "
        "Please upload a CSV file with your metrics data.",
    ),
    (
        b"GIF8",
        "This is a GIF image, not a CSV. "
        "Please upload a CSV file with your metrics data.",
    ),
]

# ─── Filename cleaning patterns ───────────────────────────────────────────────
# Leading date: 2026-03-29_  /  03-29-2026_  /  20260329_
_LEADING_DATE_RE = re.compile(
    r"^(?:\d{4}[_\-]\d{2}[_\-]\d{2}[_\-\s]*|"
    r"\d{2}[_\-]\d{2}[_\-]\d{4}[_\-\s]*|"
    r"\d{8}[_\-\s]*)"
)
# Trailing junk suffixes — applied iteratively until stable
_TRAILING_JUNK_RE = re.compile(
    r"[_\-\s]?"
    r"(?:template|data|report|export|download|sample|example|"
    r"final|backup|copy|draft|v\d+(?:\.\d+)*|version\s*\d+|\d+)$",
    re.IGNORECASE,
)

# ─── Number parsing helpers ───────────────────────────────────────────────────
_CURRENCY_STRIP_RE = re.compile(r"[$₹€£¥]")


def _check_binary(raw: bytes) -> Optional[str]:
    """Return an actionable error message if *raw* looks like a binary file, else None."""
    for sig, msg in _BINARY_SIGNATURES:
        if raw[: len(sig)] == sig:
            return msg
    # Heuristic: too many non-printable bytes → not a text/CSV file
    sample = raw[:512]
    if sample:
        non_printable = sum(1 for b in sample if b < 9 or (13 < b < 32) or b == 127)
        if non_printable / len(sample) > 0.30:
            return (
                "This file does not appear to be a CSV — it may be a binary or compressed file. "
                "Please export your data as a plain CSV (comma-separated values) file and try again."
            )
    return None


def _detect_encoding(raw: bytes) -> str:
    """
    Detect text encoding of *raw*.
    Priority: UTF-8 BOM → UTF-8 → chardet (≥70 % confidence) → Latin-1.
    """
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        import chardet
        result = chardet.detect(raw[:4096])
        enc = (result.get("encoding") or "").strip()
        confidence = result.get("confidence") or 0.0
        if enc and confidence >= 0.70:
            try:
                raw.decode(enc)
                return enc
            except (UnicodeDecodeError, LookupError):
                pass
    except ImportError:
        pass
    return "latin-1"


def _detect_delimiter(text: str) -> str:
    """Auto-detect delimiter; falls back to comma."""
    try:
        sample = "\n".join(text.splitlines()[:15])
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        if dialect.delimiter in {",", ";", "\t", "|"}:
            return dialect.delimiter
    except csv.Error:
        pass
    return ","


def _find_column(fieldnames_map: dict[str, str], canonical: str) -> Optional[str]:
    """
    Find the first actual column name matching *canonical* or any of its aliases.

    *fieldnames_map* maps normalised_key (lowercase, spaces→underscores) → original header.
    Returns the original header string, or None if not matched.
    """
    for alias in _COL_ALIASES.get(canonical, []):
        # Normalise alias the same way as the fieldnames_map keys
        norm = alias.strip().lower().replace(" ", "_")
        if norm in fieldnames_map:
            return fieldnames_map[norm]
    return None


def _parse_number(val: str) -> Optional[float]:
    """
    Convert a raw string to float, supporting:
    - Currency symbols ($, ₹, €, £, ¥)
    - Percent suffix (%)
    - K / M / B suffixes (case-insensitive)
    - European decimal format: 1.234,56  →  1234.56
    - Space as thousand separator: 1 234.56
    - Comma-as-decimal (European): 3,14  →  3.14
    - Standard comma-as-thousands: 1,234  →  1234

    Returns None for empty/unparseable input.
    """
    if not val or not val.strip():
        return None
    s = val.strip()

    # Strip currency symbols
    s = _CURRENCY_STRIP_RE.sub("", s).strip()
    # Strip percent
    if s.endswith("%"):
        s = s[:-1].strip()
    if not s:
        return None

    # K / M / B multiplier
    multiplier = 1.0
    if s and s[-1].upper() in ("K", "M", "B"):
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}[s[-1].upper()]
        s = s[:-1].strip()

    # Handle mixed comma/dot — determine which is decimal separator
    has_dot   = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        last_dot   = s.rfind(".")
        last_comma = s.rfind(",")
        if last_comma > last_dot:
            # European: 1.234,56 → dots=thousands, comma=decimal
            s = s.replace(".", "").replace(",", ".")
        else:
            # Standard: 1,234.56 → commas=thousands
            s = s.replace(",", "")
    elif has_comma:
        # Comma only — disambiguate
        parts = s.split(",")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            if len(parts[1]) <= 2:
                # Looks like decimal: 3,14 or 45,50
                s = s.replace(",", ".")
            else:
                # Looks like thousands: 1,000 or 12,345
                s = s.replace(",", "")
        else:
            s = s.replace(",", "")

    # Strip space-as-thousands separator
    s = s.replace(" ", "")
    if not s:
        return None

    try:
        return float(s) * multiplier
    except ValueError:
        logger.warning("Could not parse numeric value: %r (cleaned: %r)", val, s)
        return None


def _detect_unit_from_value(raw: str) -> Optional[str]:
    """Return 'currency' or 'percent' if the raw value string contains a symbol."""
    s = raw.strip()
    if any(sym in s for sym in ("$", "₹", "€", "£", "¥")):
        return "currency"
    if s.endswith("%"):
        return "percent"
    return None


def _normalise_unit(raw_unit: str, metric_name: str, raw_value: str) -> str:
    """
    Return one of 'currency' | 'percent' | 'number'.

    Resolution order:
    1. Explicit unit column value  →  _UNIT_ALIASES lookup
    2. Value string symbols        →  _detect_unit_from_value
    3. Metric name keywords        →  _NAME_UNIT_HINTS patterns
    4. Default                     →  'number'
    """
    if raw_unit:
        key = raw_unit.lower().strip()
        if key in _UNIT_ALIASES:
            return _UNIT_ALIASES[key]
        # Single-char symbol in the unit field (e.g. column value is just "$")
        for sym, mapped in (("%", "percent"), ("$", "currency"), ("₹", "currency"),
                             ("€", "currency"), ("£", "currency"), ("¥", "currency")):
            if key == sym:
                return mapped

    from_val = _detect_unit_from_value(raw_value)
    if from_val:
        return from_val

    for pattern, unit in _NAME_UNIT_HINTS:
        if pattern.search(metric_name):
            return unit

    return "number"


# ─── Brand name correct capitalisation ───────────────────────────────────────
# Maps lowercase word → correctly capitalised brand name.
# Applied word-by-word after title-casing so 'Tiktok Ads' → 'TikTok Ads'.
_BRAND_NAMES: dict[str, str] = {
    "tiktok":    "TikTok",
    "linkedin":  "LinkedIn",
    "facebook":  "Facebook",
    "instagram": "Instagram",
    "youtube":   "YouTube",
    "mailchimp": "Mailchimp",
    "shopify":   "Shopify",
    "hubspot":   "HubSpot",
    "google":    "Google",
    "twitter":   "Twitter",
    "pinterest": "Pinterest",
    "snapchat":  "Snapchat",
    "whatsapp":  "WhatsApp",
    "wordpress": "WordPress",
    "woocommerce": "WooCommerce",
    "klaviyo":   "Klaviyo",
    "semrush":   "SEMrush",
    "ahrefs":    "Ahrefs",
    "ga4":       "GA4",
    "gads":      "Google Ads",
}


def _apply_brand_names(name: str) -> str:
    """
    Replace words in *name* with their correct brand capitalisation.

    Operates word-by-word so compound names like 'TikTok Ads' are handled
    correctly even when the source title-cased them as 'Tiktok Ads'.
    Multi-word brand entries (e.g. 'Google Ads' from 'gads') replace the
    whole word in-place.
    """
    words = name.split()
    result: list[str] = []
    i = 0
    while i < len(words):
        word_lower = words[i].lower()
        brand = _BRAND_NAMES.get(word_lower)
        if brand:
            # Multi-word brand replacement (e.g. 'gads' → 'Google Ads')
            brand_words = brand.split()
            result.extend(brand_words)
        else:
            result.append(words[i])
        i += 1
    return " ".join(result)


# ─── Filename cleaning ────────────────────────────────────────────────────────

def _clean_source_name(filename: str) -> str:
    """
    Derive a human-readable source name from a filename.

    Processing steps:
    1. Strip the .csv extension.
    2. Strip a leading date prefix  (2026-03-29_, 20260329_, 03-29-2026_).
    3. Iteratively strip common trailing suffixes until stable
       (template, data, report, export, download, sample, example,
        final, backup, copy, draft, v2, version1, etc.)
    4. Replace underscores/hyphens with spaces and title-case the result.

    Examples:
        tiktok_ads_template.csv         →  TikTok Ads
        2026-03-29_linkedin_ads_v2.csv  →  Linkedin Ads
        Shopify_Export_Final.csv        →  Shopify
        mailchimp.csv                   →  Mailchimp
    """
    name = filename
    if name.lower().endswith(".csv"):
        name = name[:-4]

    # Strip leading date prefix
    name = _LEADING_DATE_RE.sub("", name).strip("_- ")

    # Iteratively strip trailing junk suffixes (up to 8 passes for stacked suffixes)
    for _ in range(8):
        stripped = _TRAILING_JUNK_RE.sub("", name).strip("_- ")
        if stripped == name or not stripped:
            break
        name = stripped

    name = name.replace("_", " ").replace("-", " ")
    name = name.strip().title()
    return _apply_brand_names(name)


# ─── Main parser ─────────────────────────────────────────────────────────────

def parse_kpi_csv(file_content: bytes, filename: str) -> dict:
    """
    Parse a CSV file containing KPI metrics.

    Required columns (case-insensitive; aliases accepted — see _COL_ALIASES):
        metric_name   /  metric / name / kpi / indicator / measure / label
        current_value /  current / value / actual / this_period / amount

    Optional columns:
        previous_value /  previous / prev / last_period / prior / compare
        unit           /  type / format / metric_type

    Returns:
        {
            "source_name": str,
            "metrics": [
                {
                    "name": str,
                    "current_value": float,
                    "previous_value": float | None,
                    "unit": str,            # "currency" | "percent" | "number"
                    "change": float | None, # percentage, e.g. 12.5 means +12.5 %
                }
            ]
        }

    Raises:
        ValueError: with a clear, actionable message for every failure mode.
    """
    # ── Guard: empty upload ───────────────────────────────────────────────────
    if not file_content or not file_content.strip():
        raise ValueError(
            "File is empty. Please upload a CSV file with at least "
            "a header row and one data row."
        )

    # ── Guard: binary / non-text file ────────────────────────────────────────
    binary_err = _check_binary(file_content)
    if binary_err:
        raise ValueError(binary_err)

    # ── Decode ────────────────────────────────────────────────────────────────
    encoding = _detect_encoding(file_content)
    try:
        text = file_content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        try:
            text = file_content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise ValueError(
                "Could not read this file. "
                "Please save it with UTF-8 encoding and try again."
            ) from exc

    # Strip null bytes (common in some Windows CSV exports)
    text = text.replace("\x00", "")

    if not text.strip():
        raise ValueError(
            "File is empty after decoding. "
            "Please check the file and try again."
        )

    # ── Delimiter detection ───────────────────────────────────────────────────
    delimiter = _detect_delimiter(text)

    # ── Parse CSV ─────────────────────────────────────────────────────────────
    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(
                "The CSV file appears to be empty or has no header row. "
                "Please add a header row as the first line."
            )
        raw_rows_all = list(reader)
    except csv.Error as exc:
        raise ValueError(
            f"Could not parse this CSV: {exc}. "
            "Please ensure it is a valid CSV file with a header row."
        ) from exc

    if not raw_rows_all:
        raise ValueError(
            "CSV has headers but no data rows. "
            "Please add at least one row with a metric name and a numeric value."
        )

    # ── Normalise column names ────────────────────────────────────────────────
    fieldnames_raw: list[str] = [fn for fn in (reader.fieldnames or []) if fn and fn.strip()]
    # Map: normalised_key (lowercase, spaces→_) → original header
    fieldnames_map: dict[str, str] = {
        fn.strip().lower().replace(" ", "_"): fn
        for fn in fieldnames_raw
    }

    col_metric  = _find_column(fieldnames_map, "metric_name")
    col_current = _find_column(fieldnames_map, "current_value")

    if col_metric is None:
        found = ", ".join(fn.strip() for fn in fieldnames_raw) or "(none)"
        raise ValueError(
            "Could not find a metric name column. "
            "Expected one of: metric_name, metric, name, kpi, indicator, measure, label. "
            f"Columns found: {found}. "
            "Please rename your metric name column to 'metric_name'."
        )
    if col_current is None:
        found = ", ".join(fn.strip() for fn in fieldnames_raw) or "(none)"
        raise ValueError(
            "Could not find a current value column. "
            "Expected one of: current_value, current, value, actual, this_period, amount. "
            f"Columns found: {found}. "
            "Please rename your value column to 'current_value'."
        )

    col_previous = _find_column(fieldnames_map, "previous_value")
    col_unit     = _find_column(fieldnames_map, "unit")

    logger.info(
        "CSV columns mapped: metric_name=%r, current_value=%r, "
        "previous_value=%r, unit=%r (delimiter=%r)",
        col_metric, col_current, col_previous, col_unit, delimiter,
    )

    # ── Process data rows ─────────────────────────────────────────────────────
    metrics: list[dict] = []

    for row_index, row in enumerate(raw_rows_all, start=2):
        if len(metrics) >= MAX_METRICS:
            logger.info("CSV row limit (%d) reached. Remaining rows ignored.", MAX_METRICS)
            break

        raw_name = (row.get(col_metric) or "").strip()

        # Skip blank rows and comment lines
        if not raw_name or raw_name.startswith("#"):
            continue
        if not any((v or "").strip() for v in row.values()):
            continue  # wholly blank row

        raw_current_str = (row.get(col_current) or "").strip()
        current_value = _parse_number(raw_current_str)
        if current_value is None:
            logger.warning(
                "Row %d skipped: cannot parse current_value %r for metric %r.",
                row_index, raw_current_str, raw_name,
            )
            continue

        previous_value: Optional[float] = None
        if col_previous:
            raw_prev = (row.get(col_previous) or "").strip()
            if raw_prev:
                previous_value = _parse_number(raw_prev)

        raw_unit_str = ""
        if col_unit:
            raw_unit_str = (row.get(col_unit) or "").strip()

        unit = _normalise_unit(raw_unit_str, raw_name, raw_current_str)

        change: Optional[float] = None
        if previous_value is not None and previous_value != 0:
            change = round(
                ((current_value - previous_value) / abs(previous_value)) * 100, 2
            )

        metrics.append({
            "name":           raw_name,
            "current_value":  current_value,
            "previous_value": previous_value,
            "unit":           unit,
            "change":         change,
        })

    if not metrics:
        raise ValueError(
            "No valid metric rows found in the CSV. "
            "Ensure each row has a non-empty metric name and a numeric current value. "
            "Rows starting with '#' are treated as comments and skipped."
        )

    source_name = _clean_source_name(filename)
    logger.info("Parsed %d metrics from %r → source_name=%r", len(metrics), filename, source_name)
    return {"source_name": source_name, "metrics": metrics}


# ─── Template generator ───────────────────────────────────────────────────────

_TEMPLATES: dict[str, str] = {
    "linkedin_ads": (
        "metric_name,current_value,previous_value,unit\n"
        "Impressions,45200,38900,number\n"
        "Clicks,1340,1100,number\n"
        "Click-Through Rate,2.96,2.83,percent\n"
        "Spend,1850.00,1600.00,currency\n"
        "Cost Per Click,1.38,1.45,currency\n"
        "Leads Generated,87,71,number\n"
        "Cost Per Lead,21.26,22.54,currency\n"
        "Engagement Rate,3.5,3.1,percent\n"
        "Follower Growth,210,180,number\n"
        "Video Views,8900,7200,number\n"
    ),
    "tiktok_ads": (
        "metric_name,current_value,previous_value,unit\n"
        "Impressions,320000,275000,number\n"
        "Clicks,9800,8100,number\n"
        "Click-Through Rate,3.06,2.95,percent\n"
        "Spend,2400.00,2100.00,currency\n"
        "Cost Per Click,0.24,0.26,currency\n"
        "Video Views,185000,160000,number\n"
        "Video Completion Rate,42.5,39.8,percent\n"
        "Conversions,310,265,number\n"
        "Cost Per Conversion,7.74,7.92,currency\n"
        "Return on Ad Spend,3.8,3.5,number\n"
    ),
    "mailchimp": (
        "metric_name,current_value,previous_value,unit\n"
        "Emails Sent,12500,11800,number\n"
        "Open Rate,28.4,26.1,percent\n"
        "Click Rate,4.7,4.2,percent\n"
        "Unsubscribe Rate,0.3,0.4,percent\n"
        "Bounce Rate,1.2,1.5,percent\n"
        "Revenue Attributed,3200.00,2750.00,currency\n"
        "New Subscribers,340,290,number\n"
        "List Size,18450,18110,number\n"
        "Spam Complaints,2,4,number\n"
        "Automation Emails Sent,4200,3900,number\n"
    ),
    "shopify": (
        "metric_name,current_value,previous_value,unit\n"
        "Total Revenue,28500.00,24200.00,currency\n"
        "Orders,620,540,number\n"
        "Average Order Value,45.97,44.81,currency\n"
        "Conversion Rate,3.2,2.9,percent\n"
        "Sessions,19375,18621,number\n"
        "Returning Customer Rate,38.5,35.2,percent\n"
        "Cart Abandonment Rate,68.1,70.4,percent\n"
        "Refund Rate,2.1,2.6,percent\n"
        "Units Sold,1450,1260,number\n"
        "Top Product Revenue,5400.00,4100.00,currency\n"
    ),
    "generic": (
        "metric_name,current_value,previous_value,unit\n"
        "Metric One,1000,900,number\n"
        "Metric Two,55.5,50.0,percent\n"
        "Metric Three,7800.00,6500.00,currency\n"
        "Metric Four,320,280,number\n"
        "Metric Five,4.8,4.2,number\n"
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
