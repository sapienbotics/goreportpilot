"""
Format detection, table extraction, and column profiling.

This is the deterministic half of universal CSV ingestion. It answers "what is
in this file?" without any LLM involvement, and produces a *bounded* summary —
the column profile — that the mapper sends to GPT-4.1.

Bounded matters: the profile is ~120 tokens per column regardless of whether the
file has 10 rows or 500,000, so ingestion cost does not scale with file size and
a large export can never blow the context window.

Reuses services.csv_parser for encoding detection, delimiter sniffing, and
number parsing — that code is well-tested and handles European decimals, K/M/B
suffixes, and currency symbols correctly. Nothing is reimplemented here.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from services.csv_parser import (
    _check_binary,
    _detect_delimiter,
    _detect_encoding,
    _parse_number,
)

logger = logging.getLogger(__name__)

# Guardrails. The old KPI-only path capped uploads at 1 MB, which is far too
# small for a real ad-platform export.
MAX_FILE_BYTES = 10 * 1024 * 1024        # 10 MB
MAX_ROWS_SCANNED = 200_000               # rows read per table before truncating
MAX_COLUMNS = 80                         # columns profiled per table
SAMPLE_SIZE = 8                          # sample values reported per column

_CSV_EXTENSIONS = (".csv", ".tsv", ".txt")
_XLSX_EXTENSIONS = (".xlsx", ".xlsm")

ColumnType = str  # "number" | "date" | "text" | "empty"


class IngestError(ValueError):
    """
    Raised when a file cannot be read at all.

    The message is shown verbatim to the user, so it must say what to do next —
    never "parse error".
    """


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class RawTable:
    """One rectangular block of cells, before any interpretation."""

    sheet_name: str
    rows: list[list[str]]
    truncated: bool = False


@dataclass
class ColumnProfile:
    """What we know about one column. This is what the LLM sees."""

    name: str
    index: int
    inferred_type: ColumnType
    non_null_count: int
    distinct_count: int
    samples: list[str] = field(default_factory=list)
    min_value: float | None = None
    max_value: float | None = None
    # Locale decision voted across the whole column, so a single ambiguous cell
    # ("1,234") cannot flip the interpretation of its neighbours.
    decimal_mark: str = "."
    has_currency_symbol: bool = False
    has_percent_sign: bool = False
    date_format: str | None = None
    # True when every value sits in [0, 1] and no '%' appears anywhere in the
    # column. Meta and Google Ads both export rates this way — CTR 0.0047 means
    # 0.47%. Rendered as-is it reads "0.0047%" on a client's slide.
    looks_like_fraction: bool = False

    def for_prompt(self) -> dict[str, Any]:
        """Compact representation sent to the model — no raw file content beyond samples."""
        out: dict[str, Any] = {
            "column": self.name,
            "index": self.index,
            "type": self.inferred_type,
            "non_null": self.non_null_count,
            "distinct": self.distinct_count,
            "samples": self.samples,
        }
        if self.inferred_type == "number":
            out["min"] = self.min_value
            out["max"] = self.max_value
            if self.has_currency_symbol:
                out["has_currency_symbol"] = True
            if self.has_percent_sign:
                out["has_percent_sign"] = True
            if self.looks_like_fraction:
                # Told to the model so it labels the column as a rate, and used
                # deterministically at normalisation time to scale it.
                out["values_are_fractions_0_to_1"] = True
        if self.date_format:
            out["date_format"] = self.date_format
        return out


@dataclass
class TableProfile:
    """A profiled table, ready for mapping."""

    sheet_name: str
    header_row_index: int
    columns: list[ColumnProfile]
    data_row_count: int
    totals_row_index: int | None = None
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)

    # Retained for normalisation; never sent to the LLM.
    _rows: list[list[str]] = field(default_factory=list, repr=False)
    # The rows above the header — an export's own banner. Discarded for
    # mapping (they are not data) but read at normalisation time for the
    # "Currency: USD" line platforms put there. Never sent to the LLM.
    _preamble_rows: list[list[str]] = field(default_factory=list, repr=False)

    @property
    def column_fingerprint(self) -> str:
        """
        Stable hash of the header row, used to auto-match a saved mapping.

        Order-insensitive and case-insensitive so a re-export with reordered or
        re-cased columns still matches last month's mapping.
        """
        import hashlib

        normalised = sorted(
            re.sub(r"[^a-z0-9]+", "", c.name.lower()) for c in self.columns
        )
        return hashlib.sha256("|".join(normalised).encode("utf-8")).hexdigest()[:32]

    def for_prompt(self) -> dict[str, Any]:
        return {
            "sheet": self.sheet_name,
            "row_count": self.data_row_count,
            "columns": [c.for_prompt() for c in self.columns],
        }


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_tables(file_content: bytes, filename: str) -> list[RawTable]:
    """
    Turn an uploaded file into one or more raw tables.

    CSV/TSV yields exactly one table; xlsx yields one per non-empty sheet.
    Raises IngestError with an actionable message on anything unreadable.
    """
    if not file_content:
        raise IngestError(
            "That file is empty. Export your data again and re-upload it."
        )
    if len(file_content) > MAX_FILE_BYTES:
        raise IngestError(
            f"That file is {len(file_content) / 1024 / 1024:.1f} MB. "
            f"The limit is {MAX_FILE_BYTES // 1024 // 1024} MB — "
            "try exporting a shorter date range."
        )

    name = (filename or "").lower()
    is_xlsx = name.endswith(_XLSX_EXTENSIONS) or file_content[:4] == b"PK\x03\x04"

    if is_xlsx:
        return _load_xlsx(file_content)
    if name.endswith(".xls"):
        raise IngestError(
            "That is an old-format Excel file (.xls). Open it in Excel or "
            "Google Sheets and save it as .xlsx or .csv, then upload again."
        )

    # Reuse the existing binary sniffing for PDFs, images, and the like.
    binary_error = _check_binary(file_content)
    if binary_error:
        raise IngestError(binary_error)

    return [_load_delimited(file_content)]


def _load_delimited(file_content: bytes) -> RawTable:
    encoding = _detect_encoding(file_content)
    try:
        text = file_content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        text = file_content.decode("latin-1", errors="replace")

    text = text.replace("\x00", "")
    if not text.strip():
        raise IngestError(
            "That file has no readable content. Check the export and try again."
        )

    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    rows: list[list[str]] = []
    truncated = False
    for i, row in enumerate(reader):
        if i >= MAX_ROWS_SCANNED:
            truncated = True
            break
        rows.append([(cell or "").strip() for cell in row])

    if not rows:
        raise IngestError("That file has no rows.")
    return RawTable(sheet_name="Sheet1", rows=rows, truncated=truncated)


def _load_xlsx(file_content: bytes) -> list[RawTable]:
    try:
        import openpyxl  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - dependency is pinned
        raise IngestError(
            "Excel files cannot be read on this server right now. "
            "Please export as CSV instead."
        ) from exc

    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(file_content), read_only=True, data_only=True
        )
    except Exception as exc:  # noqa: BLE001
        raise IngestError(
            "That .xlsx file could not be opened — it may be corrupted or "
            "password-protected. Try re-saving it, or export as CSV."
        ) from exc

    tables: list[RawTable] = []
    try:
        for sheet in workbook.worksheets:
            rows: list[str] = []
            truncated = False
            for i, row in enumerate(sheet.iter_rows(values_only=True)):
                if i >= MAX_ROWS_SCANNED:
                    truncated = True
                    break
                rows.append([_cell_to_str(v) for v in row])
            # Skip sheets that are entirely blank.
            if any(any(cell for cell in row) for row in rows):
                tables.append(
                    RawTable(sheet_name=sheet.title, rows=rows, truncated=truncated)
                )
    finally:
        workbook.close()

    if not tables:
        raise IngestError(
            "That workbook has no sheets with data in them."
        )
    return tables


def _cell_to_str(value: Any) -> str:
    """Render an openpyxl cell as text, keeping dates in an unambiguous form."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == datetime.min.time() else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


# ---------------------------------------------------------------------------
# Header / structure detection
# ---------------------------------------------------------------------------

def _row_is_blank(row: list[str]) -> bool:
    return not any((cell or "").strip() for cell in row)


def _detect_header_row(rows: list[list[str]]) -> int:
    """
    Find the header row.

    Platform exports routinely open with a title line, a date-range line, and a
    blank line before the real header (Google Ads, LinkedIn and Meta all do
    this). The header is the first row that is mostly non-empty text and is
    followed by a row containing numbers.
    """
    best_index = 0
    best_score = -1.0

    for i, row in enumerate(rows[:12]):
        if _row_is_blank(row):
            continue
        filled = [c for c in row if c.strip()]
        if len(filled) < 2:
            continue

        # Headers are text, not numbers.
        text_cells = sum(1 for c in filled if _parse_number(c) is None)
        text_ratio = text_cells / len(filled)
        # Headers are distinct.
        distinct_ratio = len(set(c.lower() for c in filled)) / len(filled)
        # Headers are followed by data.
        next_rows = rows[i + 1 : i + 4]
        has_data_below = any(
            any(_parse_number(c) is not None for c in r if c.strip())
            for r in next_rows
            if not _row_is_blank(r)
        )

        score = text_ratio + distinct_ratio + (1.0 if has_data_below else 0.0)
        score += len(filled) / max(len(row), 1)  # prefer fully populated rows
        if score > best_score:
            best_score = score
            best_index = i

    return best_index


# Totals-row labels. Not English-only: we support 13 report languages and
# platform exports are localised, so a German "Gesamt" row must be recognised
# for the same reason an English "Total" row is.
_TOTALS_LABELS: frozenset[str] = frozenset({
    "total", "totals", "grand total", "sum", "subtotal", "overall", "all",
    "gesamt", "gesamtsumme", "summe",              # de
    "totaal",                                       # nl
    "totale", "totali",                             # it
    "totales", "suma",                              # es
    "somme", "total général",                       # fr
    "soma",                                         # pt
    "итого", "всего",                               # ru
    "合計", "総計",                                  # ja
    "总计", "合计",                                  # zh
    "कुल",                                           # hi
    "—", "-", "--",
})


def _detect_totals_row(
    rows: list[list[str]],
    numeric_columns: list[int],
    marks: dict[int, str] | None = None,
) -> int | None:
    """
    Detect a trailing totals row.

    A totals row is the last non-blank row whose numeric cells equal the sum of
    the rows above (within 0.5% for the platform's own rounding), or whose first
    cell is a totals label in any of our supported languages.

    ``marks`` carries each column's resolved decimal mark. Without it this
    comparison is done with locale-naive parsing, which reads German
    dot-thousands ("12.450") as 12.45 — so the column sums disagree with the
    totals row, the row survives, and everything downstream is poisoned by it.
    """
    if not rows or not numeric_columns:
        return None
    marks = marks or {}

    last_index = None
    for i in range(len(rows) - 1, -1, -1):
        if not _row_is_blank(rows[i]):
            last_index = i
            break
    if last_index is None or last_index == 0:
        return None

    last_row = rows[last_index]
    first_cell = (last_row[0] if last_row else "").strip().lower()
    if first_cell in _TOTALS_LABELS:
        return last_index

    body = rows[:last_index]
    matches = 0
    checked = 0
    for col in numeric_columns:
        mark = marks.get(col, ".")
        total = _parse_localized(last_row[col], mark) if col < len(last_row) else None
        if total is None:
            continue
        column_sum = 0.0
        seen = False
        for row in body:
            value = _parse_localized(row[col], mark) if col < len(row) else None
            if value is not None:
                column_sum += value
                seen = True
        if not seen:
            continue
        checked += 1
        if abs(total) > 0 and abs(column_sum - total) / abs(total) <= 0.005:
            matches += 1

    # Require agreement on most numeric columns — one coincidental match is not
    # enough to throw away a row of real data.
    if checked >= 2 and matches / checked >= 0.75:
        return last_index
    return None


def _likely_numeric_columns(rows: list[list[str]], width: int) -> list[int]:
    """
    Cheap first pass to find numeric columns, used only to locate the totals row.

    Sampled rather than exhaustive because it runs before profiling and its only
    consumer is a heuristic.
    """
    sample = rows[: min(len(rows), 200)]
    numeric: list[int] = []
    for index in range(width):
        values = [
            row[index] for row in sample
            if index < len(row) and row[index].strip()
        ]
        if not values:
            continue
        hits = sum(1 for v in values if _parse_number(v) is not None)
        if hits / len(values) >= 0.80:
            numeric.append(index)
    return numeric


def _forward_fill_header(header: list[str]) -> list[str]:
    """
    Fill blanks left by merged header cells.

    Merged cells arrive as ["Clicks", "", "", "Spend"]; the blanks belong to the
    heading on their left. Columns still without a name become "Column N" so
    they can be referenced in the mapping UI.
    """
    out: list[str] = []
    last = ""
    for i, cell in enumerate(header):
        name = (cell or "").strip()
        if name:
            last = name
            out.append(name)
        elif last:
            # Blank cell under a merged heading — inherit it. The duplicate
            # suffixing below turns these into "Clicks", "Clicks (2)", …
            out.append(last)
        else:
            out.append(f"Column {i + 1}")

    # Disambiguate duplicates so mappings can address columns unambiguously.
    seen: dict[str, int] = {}
    final: list[str] = []
    for name in out:
        if name in seen:
            seen[name] += 1
            final.append(f"{name} ({seen[name]})")
        else:
            seen[name] = 1
            final.append(name)
    return final


# ---------------------------------------------------------------------------
# Column profiling
# ---------------------------------------------------------------------------

def _parse_localized(raw: Any, decimal_mark: str) -> float | None:
    """
    Parse one cell using its column's resolved decimal mark.

    The shared _parse_number guesses per cell, which reads "1,234" and "1,23"
    inconsistently within the same column. Here the mark is already settled, so
    the value is normalised to canonical form first and _parse_number then
    handles currency symbols, percent signs, and K/M/B suffixes as usual.

    This is the single number-parsing entry point for universal ingestion —
    profiling and normalisation both call it, so a column's min/max can never
    disagree with the values that end up in the report.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if decimal_mark == ",":
        s = s.replace(".", "").replace(",", ".")
    return _parse_number(s)


def _pick_samples(values: list[str]) -> list[str]:
    """
    Choose representative sample values: first 2, last 2, and 4 spread evenly
    through the middle.

    Head-only sampling is what makes naive importers miss trailing totals rows
    and mid-file format changes, so the tail is always represented.
    """
    non_empty = [v for v in values if v.strip()]
    if len(non_empty) <= SAMPLE_SIZE:
        return non_empty

    picks = [0, 1, len(non_empty) - 2, len(non_empty) - 1]
    middle_count = SAMPLE_SIZE - len(picks)
    step = len(non_empty) / (middle_count + 1)
    picks += [int(step * (k + 1)) for k in range(middle_count)]

    seen: set[int] = set()
    out: list[str] = []
    for index in sorted(picks):
        index = max(0, min(index, len(non_empty) - 1))
        if index not in seen:
            seen.add(index)
            out.append(non_empty[index])
    return out[:SAMPLE_SIZE]


@dataclass
class _LocaleVote:
    """Evidence about which separator is the decimal point."""

    comma_decimal: int = 0
    dot_decimal: int = 0
    # Values like "1.234" / "2.500" — a dot followed by exactly three digits.
    # On its own this is genuinely ambiguous (European thousands, or a
    # four-significant-figure decimal), so it is counted separately and only
    # resolved using evidence from the rest of the file.
    dot_triple: int = 0
    comma_triple: int = 0

    def add(self, other: "_LocaleVote") -> None:
        self.comma_decimal += other.comma_decimal
        self.dot_decimal += other.dot_decimal
        self.dot_triple += other.dot_triple
        self.comma_triple += other.comma_triple

    @property
    def decisive_mark(self) -> str | None:
        if self.comma_decimal > self.dot_decimal:
            return ","
        if self.dot_decimal > self.comma_decimal:
            return "."
        return None


def _vote_decimal_mark(values: list[str]) -> _LocaleVote:
    """
    Gather separator evidence for one column.

    Per-cell guessing reads "1,234" and "1,23" inconsistently, so the decision
    is made once per column — and, when a column is inconclusive, once per file
    (see _profile_locale). Locale is a property of the export, not of a column:
    an export with "1.234,56" anywhere in it is European throughout.
    """
    vote = _LocaleVote()
    for raw in values[:500]:
        s = raw.strip()
        if not s:
            continue
        has_dot, has_comma = "." in s, "," in s
        if has_dot and has_comma:
            # Whichever separator comes last is the decimal one. This case is
            # unambiguous and is the strongest evidence available.
            if s.rfind(",") > s.rfind("."):
                vote.comma_decimal += 1
            else:
                vote.dot_decimal += 1
        elif has_comma:
            tail = s.rsplit(",", 1)[-1]
            if tail.isdigit() and len(tail) <= 2:
                vote.comma_decimal += 1      # "12,5" — comma is the decimal point
            elif tail.isdigit() and len(tail) == 3:
                vote.comma_triple += 1       # "12,500" — probably thousands
        elif has_dot:
            tail = s.rsplit(".", 1)[-1]
            if tail.isdigit() and len(tail) <= 2:
                vote.dot_decimal += 1        # "12.5" — dot is the decimal point
            elif tail.isdigit() and len(tail) == 3:
                vote.dot_triple += 1         # "12.500" — ambiguous
    return vote


def _resolve_mark(column_vote: _LocaleVote, file_vote: _LocaleVote) -> str:
    """
    Settle one column's decimal mark: its own decisive evidence, then the
    file's, then the ambiguous triple-digit groups, then the default.
    """
    mark = column_vote.decisive_mark or file_vote.decisive_mark
    if mark:
        return mark
    # No decisive evidence anywhere. Triple-digit groups after a separator are
    # then the only signal: "1.234" alongside "2.500" and "3.100" in the same
    # column is thousands notation, not three-decimal-place precision.
    if file_vote.dot_triple > file_vote.comma_triple and file_vote.dot_triple >= 2:
        return ","      # dots are thousands separators -> comma would be decimal
    return "."


# Ranked date formats. Ordering matters: ISO first, then the unambiguous
# month-name forms, then the ambiguous numeric ones.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%Y%m%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
    "%Y-%m",
    "%b %Y",
    "%B %Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d.%m.%Y",
)

_DMY_FORMATS = {"%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"}
_MDY_FORMATS = {"%m/%d/%Y", "%m-%d-%Y"}

# A format is only accepted if it parses this fraction of the column.
_DATE_MATCH_THRESHOLD = 0.95


def detect_date_format(values: list[str]) -> str | None:
    """
    Return the strftime format that parses this column, or None.

    Requires 95% of non-empty values to parse, so a numeric column with a few
    slash-separated strings in it is never mistaken for dates.

    DMY/MDY ambiguity (03/04/2026) is resolved by looking for any value whose
    first component exceeds 12 — that settles it. When nothing settles it we
    return the DMY reading but the caller surfaces it for user confirmation,
    because guessing silently here corrupts an entire time series.
    """
    sample = [v.strip() for v in values if v.strip()][:400]
    if not sample:
        return None

    for fmt in _DATE_FORMATS:
        parsed = 0
        for raw in sample:
            try:
                datetime.strptime(raw, fmt)
                parsed += 1
            except ValueError:
                continue
        if parsed / len(sample) < _DATE_MATCH_THRESHOLD:
            continue

        if fmt in _DMY_FORMATS or fmt in _MDY_FORMATS:
            return _resolve_day_month_order(sample, fmt)
        return fmt
    return None


def _resolve_day_month_order(sample: list[str], fmt: str) -> str:
    """Pick between DMY and MDY using any value with a component above 12."""
    separator = "/" if "/" in fmt else ("-" if "-" in fmt else ".")
    first_over_12 = False
    second_over_12 = False
    for raw in sample:
        parts = raw.split(separator)
        if len(parts) < 2:
            continue
        try:
            first, second = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if first > 12:
            first_over_12 = True
        if second > 12:
            second_over_12 = True

    if first_over_12 and not second_over_12:
        return {"%m/%d/%Y": "%d/%m/%Y", "%m-%d-%Y": "%d-%m-%Y"}.get(fmt, fmt)
    if second_over_12 and not first_over_12:
        return {"%d/%m/%Y": "%m/%d/%Y", "%d-%m-%Y": "%m-%d-%Y"}.get(fmt, fmt)
    return fmt


def _infer_type(values: list[str], date_format: str | None) -> ColumnType:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "empty"
    if date_format:
        return "date"
    numeric = sum(1 for v in non_empty if _parse_number(v) is not None)
    if numeric / len(non_empty) >= 0.80:
        return "number"
    return "text"


def profile_table(table: RawTable) -> TableProfile:
    """Profile one raw table: header, columns, totals row."""
    rows = [r for r in table.rows]
    if not rows:
        raise IngestError("That sheet has no rows.")

    header_index = _detect_header_row(rows)
    header = _forward_fill_header(rows[header_index])[:MAX_COLUMNS]
    body = [r for r in rows[header_index + 1 :] if not _row_is_blank(r)]

    warnings: list[str] = []
    if len(rows[header_index]) > MAX_COLUMNS:
        warnings.append(
            f"Only the first {MAX_COLUMNS} columns were read; "
            f"this file has {len(rows[header_index])}."
        )

    numeric_indices = _likely_numeric_columns(body, len(header))

    # Resolve locale FIRST, then find the totals row, then profile.
    #
    # The order is load-bearing and was wrong before: totals detection compares
    # each column's sum against the last row, and doing that with locale-naive
    # parsing reads German dot-thousands ("12.450") as 12.45. The sums then
    # disagree, the totals row survives, its "Gesamt" label sits in the date
    # column, and only 5 of 6 values parse as dates — below the 95% threshold,
    # so the time dimension is silently lost. One ordering mistake, four
    # downstream symptoms.
    column_votes: dict[int, _LocaleVote] = {}
    file_vote = _LocaleVote()
    for index in numeric_indices:
        values = [
            row[index] for row in body
            if index < len(row) and row[index].strip()
        ]
        vote = _vote_decimal_mark(values)
        column_votes[index] = vote
        file_vote.add(vote)
    marks = {
        index: _resolve_mark(column_votes[index], file_vote)
        for index in numeric_indices
    }

    totals_index = _detect_totals_row(body, numeric_indices, marks)
    data_rows = (
        [r for i, r in enumerate(body) if i != totals_index]
        if totals_index is not None
        else body
    )

    raw_by_index: dict[int, list[str]] = {
        index: [(row[index] if index < len(row) else "") for row in data_rows]
        for index in range(len(header))
    }

    columns: list[ColumnProfile] = []

    for index, name in enumerate(header):
        raw_values = raw_by_index[index]
        non_empty = [v for v in raw_values if v.strip()]

        date_format = detect_date_format(raw_values)
        inferred = _infer_type(raw_values, date_format)

        profile = ColumnProfile(
            name=name,
            index=index,
            inferred_type=inferred,
            non_null_count=len(non_empty),
            distinct_count=len(set(non_empty)),
            samples=_pick_samples(raw_values),
            date_format=date_format,
        )

        if inferred == "number":
            profile.decimal_mark = marks.get(
                index, _resolve_mark(_vote_decimal_mark(non_empty), file_vote)
            )
            # Min/max must be read with the resolved locale, otherwise a
            # European column reports 3.1 where the real maximum is 3,100.
            numbers = [
                n for n in (
                    _parse_localized(v, profile.decimal_mark) for v in non_empty
                )
                if n is not None
            ]
            if numbers:
                profile.min_value = round(min(numbers), 4)
                profile.max_value = round(max(numbers), 4)
            profile.has_currency_symbol = any(
                sym in v for v in non_empty[:200] for sym in ("$", "₹", "€", "£", "¥")
            )
            profile.has_percent_sign = any("%" in v for v in non_empty[:200])
            # A rate stored as a fraction. Requires the whole column to sit in
            # [0, 1] AND carry no '%' anywhere — a column already written as
            # "0.91%" is a percentage and must not be scaled again. Integers-only
            # columns are excluded so a column of zeros and ones (a flag) is not
            # mistaken for a rate.
            profile.looks_like_fraction = bool(
                numbers
                and not profile.has_percent_sign
                and not profile.has_currency_symbol
                and profile.min_value is not None
                and profile.min_value >= 0.0
                and profile.max_value is not None
                and profile.max_value <= 1.0
                and any(not float(n).is_integer() for n in numbers)
            )

        columns.append(profile)

    if totals_index is not None:
        warnings.append(
            f"Row {totals_index + header_index + 2} looks like a totals row "
            "and was excluded so it isn't double-counted."
        )

    if table.truncated:
        warnings.append(
            f"Only the first {MAX_ROWS_SCANNED:,} rows were read."
        )

    return TableProfile(
        sheet_name=table.sheet_name,
        header_row_index=header_index,
        columns=columns,
        data_row_count=len(data_rows),
        totals_row_index=totals_index,
        truncated=table.truncated,
        warnings=warnings,
        _rows=body,
        _preamble_rows=[r for r in rows[:header_index] if not _row_is_blank(r)],
    )


def profile_file(file_content: bytes, filename: str) -> list[TableProfile]:
    """Load and profile every table in an uploaded file."""
    profiles = [profile_table(table) for table in load_tables(file_content, filename)]
    # Largest rectangular table first — that is nearly always the real data,
    # with summary tabs and read-me sheets trailing behind it.
    profiles.sort(
        key=lambda p: (p.data_row_count * max(len(p.columns), 1)), reverse=True
    )
    return profiles
