"""
Which currency an uploaded file's money columns are actually in.

Without this the report renders every CSV monetary figure in the account's
default currency symbol. The LinkedIn Ads fixture states "Currency: USD" in
its preamble and its spend totals $199,457.12; the deck rendered "₹107,135".
A wrong number is obvious and gets caught. A right number wearing the wrong
currency symbol reads as correct all the way to the client.

Three sources, most authoritative first:

  1. A preamble line above the header — "Currency: USD", "Currency,GBP".
     Explicit, written by the exporting platform.
  2. A currency named or symbolised in a money column's header —
     "Total Spent (USD)", "Cost [$]", "Spend €".
  3. A symbol in the cells themselves — "$1,234.56".

Returns an ISO 4217 code, or None when nothing is detectable — the caller
then falls back to the account default, which is the old behaviour and the
only honest answer when the file does not say.
"""
from __future__ import annotations

import re

# Symbols that map to exactly one currency. '$' and '¥' are deliberately
# absent: '$' is USD, CAD, AUD, SGD, HKD, MXN, BRL and more, and guessing
# between them is how you mislabel a report with confidence. They are handled
# separately, below, and only ever resolve when a prefix disambiguates them.
_UNAMBIGUOUS_SYMBOLS: dict[str, str] = {
    "₹": "INR",
    "€": "EUR",
    "£": "GBP",
    "₽": "RUB",
    "₩": "KRW",
    "₺": "TRY",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "S$": "SGD",
    "HK$": "HKD",
    "NZ$": "NZD",
    "Mex$": "MXN",
    "RM": "MYR",
    "₪": "ILS",
    "₦": "NGN",
    "฿": "THB",
    "₫": "VND",
    "₱": "PHP",
}

# Codes we accept when written out explicitly.
_KNOWN_CODES: frozenset[str] = frozenset({
    "USD", "EUR", "GBP", "INR", "AUD", "CAD", "JPY", "CNY", "BRL", "MXN",
    "SGD", "HKD", "CHF", "SEK", "NOK", "DKK", "ZAR", "AED", "SAR", "MYR",
    "NZD", "PLN", "TRY", "RUB", "KRW", "THB", "IDR", "PHP", "VND", "ILS",
    "NGN", "KES", "EGP", "CZK", "HUF", "RON", "CLP", "COP", "ARS", "PEN",
})

_PREAMBLE_KEYS = ("currency", "currency code", "reporting currency",
                  "account currency", "devise", "währung", "moneda")

# "Currency: USD" / "Currency,USD" / "Reporting Currency = GBP"
_PREAMBLE_RE = re.compile(
    r"^\s*(" + "|".join(re.escape(k) for k in _PREAMBLE_KEYS) + r")\s*[:=,]\s*(.+)$",
    re.IGNORECASE,
)

# A bare code appearing as a word: "Total Spent (USD)", "Cost in EUR"
_CODE_IN_TEXT_RE = re.compile(r"(?<![A-Za-z])([A-Z]{3})(?![A-Za-z])")


def _code_from_text(text: str) -> str | None:
    """An explicit ISO code, or an unambiguous symbol, inside a string."""
    if not text:
        return None

    for match in _CODE_IN_TEXT_RE.finditer(text.upper()):
        if match.group(1) in _KNOWN_CODES:
            return match.group(1)

    # Longest symbols first so "R$" wins over a bare "R", and "HK$" over "$".
    for symbol in sorted(_UNAMBIGUOUS_SYMBOLS, key=len, reverse=True):
        if symbol in text:
            return _UNAMBIGUOUS_SYMBOLS[symbol]

    return None


def from_preamble(preamble_rows: list[list[str]]) -> str | None:
    """A 'Currency: USD' line in the rows above the header."""
    for row in preamble_rows:
        # Join so both "Currency: USD" in one cell and "Currency" | "USD"
        # across two cells are matched by the same expression.
        joined = ",".join(cell.strip() for cell in row if cell and cell.strip())
        if not joined:
            continue
        match = _PREAMBLE_RE.match(joined)
        if match:
            found = _code_from_text(match.group(2))
            if found:
                return found
    return None


def from_headers(header_names: list[str]) -> str | None:
    """A currency named in a column header — "Total Spent (USD)"."""
    for name in header_names:
        found = _code_from_text(name or "")
        if found:
            return found
    return None


def from_samples(samples: list[str]) -> str | None:
    """A currency symbol in the cells themselves — "€1.234,56"."""
    for sample in samples:
        found = _code_from_text(sample or "")
        if found:
            return found
    return None


def detect(
    preamble_rows: list[list[str]],
    money_headers: list[str],
    money_samples: list[str],
) -> tuple[str | None, str]:
    """
    Resolve the file's currency.

    Returns (ISO code or None, how it was found). The caller falls back to the
    account default when the code is None — never guesses, because a guessed
    currency symbol on a correct number is worse than an admitted default.
    """
    found = from_preamble(preamble_rows)
    if found:
        return found, "file preamble"

    found = from_headers(money_headers)
    if found:
        return found, "column header"

    found = from_samples(money_samples)
    if found:
        return found, "cell values"

    return None, "not stated in file"
