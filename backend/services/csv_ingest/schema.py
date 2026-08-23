"""
The mapping contract.

Everything that crosses the LLM boundary is defined here and validated with
Pydantic. The model's job is strictly classification — naming what each column
*is*. It never sees cell values beyond the eight samples per column, never
transforms a number, and never produces a figure that reaches a client report.
All arithmetic and locale handling stays in deterministic Python.

That split is deliberate: a mis-named column is a visible, correctable mistake;
a hallucinated number in a client's report is an unrecoverable trust failure.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

TableShape = Literal["long_kpi", "wide_timeseries", "wide_entity", "unknown"]
MetricUnit = Literal["number", "currency", "percent", "ratio", "duration"]
Direction = Literal["higher_is_better", "lower_is_better"]

# Mappings ABOVE this confidence are pre-accepted in the UI. Anything at or
# below it starts unconfirmed and blocks the Confirm button until a human
# resolves it — silently accepting a low-confidence guess is how wrong numbers
# reach clients.
#
# The boundary is exclusive on purpose. It used to be `confidence < 0.80`,
# which accepted exactly 0.80 without asking — and 0.80 is one of the most
# likely values for a model to emit, because models reach for round numbers.
# GPT-4.1 returned precisely 0.8 for the Semrush "Cost" column, a genuinely
# ambiguous header (ad spend or estimated traffic value?), and it sailed
# through unquestioned. A guardrail with a hole at its most probable input is
# not a guardrail. The cost of the stricter comparison is one extra question
# on a borderline column; the cost of the looser one is a wrong metric on a
# client's slide.
CONFIDENCE_THRESHOLD = 0.80


class ColumnMapping(BaseModel):
    """One source column mapped to one metric."""

    source_column: str
    target_metric: str = Field(
        description="snake_case canonical name, e.g. 'impressions', 'cost_per_lead'"
    )
    label: str = Field(default="", description="Human-readable label for the report")
    unit: MetricUnit = "number"
    direction: Direction = "higher_is_better"
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""

    @field_validator("target_metric")
    @classmethod
    def _slugify(cls, value: str) -> str:
        cleaned = "".join(c if c.isalnum() else "_" for c in value.strip().lower())
        return "_".join(part for part in cleaned.split("_") if part) or "metric"

    @property
    def needs_confirmation(self) -> bool:
        return self.confidence <= CONFIDENCE_THRESHOLD


class DateColumn(BaseModel):
    name: str
    format: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EntityColumn(BaseModel):
    name: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class IgnoredColumn(BaseModel):
    name: str
    reason: str = ""


class Ambiguity(BaseModel):
    """
    A question the model could not answer from the column profile alone.

    Rendered as an inline question above the mapping table. "Is 'Cost' money you
    spent or money you earned?" is worth one click; guessing wrong inverts the
    meaning of the whole report.
    """

    column: str
    candidates: list[str] = Field(default_factory=list)
    question: str


class MappingProposal(BaseModel):
    """The model's complete response. Validated before anything else touches it."""

    table_shape: TableShape = "unknown"
    source_label: str = "Custom Data"
    date_column: DateColumn | None = None
    entity_column: EntityColumn | None = None
    columns: list[ColumnMapping] = Field(default_factory=list)
    ignored_columns: list[IgnoredColumn] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)

    # Set by the service layer, not the model.
    sheet_name: str = ""
    column_fingerprint: str = ""
    origin: Literal["ai", "saved_template", "system_template", "manual"] = "ai"
    warnings: list[str] = Field(default_factory=list)

    @property
    def requires_user_input(self) -> bool:
        """True when the UI must block Confirm until a human resolves something."""
        return bool(self.ambiguities) or any(c.needs_confirmation for c in self.columns)

    def mapped_columns(self) -> list[str]:
        return [c.source_column for c in self.columns]


# The JSON Schema handed to the model. Kept explicit rather than generated so
# the prompt contract is readable in one place and can be diffed.
MAPPING_JSON_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["table_shape", "source_label", "columns"],
    "properties": {
        "table_shape": {
            "type": "string",
            "enum": ["long_kpi", "wide_timeseries", "wide_entity", "unknown"],
        },
        "source_label": {"type": "string"},
        "date_column": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "format": {"type": ["string", "null"]},
                "confidence": {"type": "number"},
            },
        },
        "entity_column": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "confidence": {"type": "number"},
            },
        },
        "columns": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_column", "target_metric", "unit", "confidence"],
                "properties": {
                    "source_column": {"type": "string"},
                    "target_metric": {"type": "string"},
                    "label": {"type": "string"},
                    "unit": {
                        "type": "string",
                        "enum": ["number", "currency", "percent", "ratio", "duration"],
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["higher_is_better", "lower_is_better"],
                    },
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
            },
        },
        "ignored_columns": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
        "ambiguities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["column", "question"],
                "properties": {
                    "column": {"type": "string"},
                    "candidates": {"type": "array", "items": {"type": "string"}},
                    "question": {"type": "string"},
                },
            },
        },
    },
}
