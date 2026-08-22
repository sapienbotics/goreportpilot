"""
Universal CSV/XLSX ingestion.

Accepts an export of arbitrary schema from any platform, works out what its
columns mean, confirms that reading with the user, and produces data the report
pipeline already knows how to render.

This is the answer to the integration-count question: we do not need a connector
for LinkedIn Ads, TikTok, Semrush or the next platform that launches, because
every one of them exports a spreadsheet.

Pipeline
--------
    profiler   deterministic. Reads the file, finds the header row, drops the
               totals row, and builds a bounded column profile.
    mapper     the only LLM step. Classifies columns; never touches values.
    schema     the contract between the two, validated with Pydantic.
    normalizer deterministic. Applies a confirmed mapping and does all the
               arithmetic, locale handling, and period comparison.
    templates  saved mappings, matched by column fingerprint, so the second
               upload of the same export needs no LLM call at all.

The existing five KPI templates live in ``templates.py`` as pre-seeded mappings
in this system rather than as a parallel code path.
"""
from services.csv_ingest.mapper import propose_mapping
from services.csv_ingest.normalizer import (
    NormalizationError,
    normalize,
    preview_rows,
)
from services.csv_ingest.profiler import (
    IngestError,
    MAX_FILE_BYTES,
    TableProfile,
    profile_file,
)
from services.csv_ingest.schema import (
    CONFIDENCE_THRESHOLD,
    Ambiguity,
    ColumnMapping,
    MappingProposal,
)

__all__ = [
    "CONFIDENCE_THRESHOLD",
    "MAX_FILE_BYTES",
    "Ambiguity",
    "ColumnMapping",
    "IngestError",
    "MappingProposal",
    "NormalizationError",
    "TableProfile",
    "normalize",
    "preview_rows",
    "profile_file",
    "propose_mapping",
]
