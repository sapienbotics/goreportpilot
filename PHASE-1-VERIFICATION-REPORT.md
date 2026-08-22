# PHASE-1-VERIFICATION-REPORT

Date: 2026-08-22
Scope: verification of D-0 (source adapter seam) and Track A (universal CSV/XLSX ingestion)
Artifacts: `C:\mnt\user-data\outputs\csv-verification\`

---

## Headline

The fixtures did their job. They found **four defects**, three in Track A code and one
pre-existing and more serious than anything in Track A:

| # | Defect | Severity | Status |
|---|---|---|---|
| 1 | Narrative fallback leaked the raw OpenAI error — including the billing URL — onto slide 2 of a **client-facing deck** | **High, pre-existing, live** | Fixed |
| 2 | Totals-row detection was locale-blind, so the German file lost its totals row *and* its date column | High | Fixed |
| 3 | Rates stored as fractions rendered as "0.0047%" instead of "0.47%" | Medium | Fixed |
| 4 | `from __future__ import annotations` + a 204 route crashed the app at import — **I took production down for ~13 minutes** | **Critical, self-inflicted** | Fixed + guard added |

Two steps could not be completed, both for external reasons, neither a code fault:

- **Step 3 (real GPT-4.1 calls)** — the OpenAI account returns `429 insufficient_quota /
  credit_balance_exhausted`. The API key authenticates correctly; the account has no credit.
- **Step 4 (apply migration)** — the Supabase connector is pointed at
  `wlincviytcnxfhnacdwv`, **not** GoReportPilot's `kbytzqviqzcvfdepjyby`. I did not apply.
- **Step 5 (browser test)** — production requires sign-in and I do not enter passwords.

---

## Step 1 — Fixtures

`backend/tests/fixtures/csv_ingest/`

| File | Targets |
|---|---|
| `linkedin_ads_export.csv` | wide timeseries, US format, CTR as "0.91%" strings |
| `google_ads_de_export.csv` | German locale, semicolons, dot-thousands, `Gesamt` totals row |
| `meta_ads_multisheet.xlsx` | decoy sheet + fractional CTR (built by `make_meta_xlsx.py`) |
| `messy_semrush_export.csv` | preamble, blank rows, ambiguous "Cost" |
| `legacy_kpi_format.csv` | regression guard: `$48,320.50`, `24.8%`, `12.4K` |
| `stub_mappings.json` | recorded mappings for `--stub` mode (added, see Step 3) |

CTR values in fixture 1 were chosen so **both halves average exactly 1.16%** — the PASS
target — while summing to 5.80. That makes the sum-vs-average distinction unambiguous
rather than approximately right.

## Step 2 — `verify_csv_ingest.py`

**41 passed, 0 failed.** Re-run after every fix below; still 41/41.

---

## Step 3 — AI mapping path

### Blocked: the OpenAI account has no credits

```
openai.RateLimitError: Error code: 429 -
  'You have no credits remaining. Add credits to continue using the API at
   https://platform.openai.com/settings/organization/billing/'
  type: insufficient_quota   code: credit_balance_exhausted
```

`client.models.list()` succeeds, so the key is valid and authenticates. This is account
billing state, not configuration.

`scripts/verify_csv_mapping_ai.py` was written as specified and now **preflights** this:
one clear failure with the cause named, instead of five cascading fixture failures that
read like mapping bugs. It also gained `--stub`, which replaces the model response with a
recorded mapping so the deterministic half stays verifiable.

**`--stub` is not a substitute and does not pretend to be.** Assertions that depend on the
model's judgement are reported as `UNVERIFIED`, never `PASS` — a stub can only verify the
code around the model.

### Result: `--stub` → 29 passed, 0 failed, 7 UNVERIFIED

| Fixture | PASS condition | Result |
|---|---|---|
| 1 LinkedIn | CTR averaged ~1.16%, not summed | **PASS** — 1.16 (sum would be 5.80) |
| 1 | Impressions/clicks/spend SUM | **PASS** — 69,100 / 804 / 1,525.35 |
| 1 | date column detected | **PASS** (profiler) / UNVERIFIED (model's choice) |
| 1 | trend chart renders | **PASS** |
| 2 German | Kosten totals 8,276.85, not 827,685 | **PASS** — 5,490.00 + 2,786.85 |
| 2 | Impressionen 55,011 not 55.011 | **PASS** |
| 2 | totals row excluded before profiling | **PASS** — *after fixing defect 2* |
| 2 | date column detected | **PASS** — `%d.%m.%Y`, *after fixing defect 2* |
| 3 xlsx | correct sheet chosen over decoy | **PASS** — "Campaign Performance" |
| 3 | spend ~332,892 INR | **PASS** — 332,892.00 |
| 3 | CTR renders as a percentage, not 0.0047 | **PASS** — 0.4975%, *after fixing defect 3* |
| 4 Semrush | header row 3, blanks skipped | **PASS** — 6 data rows |
| 4 | "Cost" raises an ambiguity | **UNVERIFIED** — depends entirely on the model |
| 4 | Confirm blocked until resolved | **PASS** — `requires_user_input` is True |
| 5 Legacy | output matches `parse_kpi_csv` | **PASS** — all 5 metrics, every field |
| all | no rate/percentage ever summed | **PASS** |
| all | no mapping below 0.80 auto-accepted | **PASS** |

The 7 unverified: table_shape detection (×2), date-column selection (×2), date-format
choice, CTR unit choice, and whether "Cost" raises an ambiguity. **Re-run
`python scripts/verify_csv_mapping_ai.py` with no flags once credits are restored.**

### Defect 1 — narrative fallback leaked internals into a client deck

Found because the credit exhaustion exercised a path nothing had exercised before.

`generate_narrative` interpolated the raw exception into `executive_summary`:

> "AI narrative generation failed: Error code: 429 - You have no credits remaining. Add
> credits to continue using the API at https://platform.openai.com/settings/organization/billing/"

That text renders on slide 2 of a deck the agency sends to *their* client. It is not
hypothetical — it is what every report generated right now would have contained.

Fixed: the fallback is neutral and internals-free. The real error is logged and returned
as `_narrative_error`, which the renderer never reads (it fetches specific keys by name)
and which `reports.sections.source_status.narrative_error` records so the dashboard can
prompt a regenerate. Verified: zero client-facing keys contain "openai", "429", "credit",
"billing", or "error code".

### Defect 2 — totals detection was locale-blind

`_detect_totals_row` ran **before** locale resolution and compared column sums using the
locale-naive `_parse_number`, which reads `12.450` as 12.45.

```
_parse_number('12.450') = 12.45      _parse_number('1.596') = 1.596
```

Sums then agreed on only 3 of 5 numeric columns (0.60, below the 0.75 threshold), so the
`Gesamt` row survived → its label sat in the `Tag` column → 5 of 6 values parsed as dates
(83%, below the 95% threshold) → **the date column was silently lost.** One ordering
mistake, four downstream symptoms.

My Phase 1 report claimed this failure mode was fixed. It was fixed for ASCII-locale files
only. The fixture caught the gap.

Fixed: locale is resolved first; the comparison uses `_parse_localized`. Totals labels are
also no longer English-only — we ship 13 report languages, so `Gesamt`, `Totale`, `合計`,
`итого` etc. now count.

### Defect 3 — fractional rates

Meta exports CTR as `0.0047` meaning 0.47%. Mapped as a percentage and rendered unscaled
that reads **"0.0047%"** on a slide.

Fixed: `ColumnProfile.looks_like_fraction` marks a numeric column whose values all sit in
[0,1] with no `%` anywhere and at least one non-integer; `normalize` scales those ×100.
Deliberately narrow — a column already written as "0.91%" carries the sign and is left
alone (verified against fixture 1). The scaling appears in `source["warnings"]` and in the
parse preview rather than happening silently.

---

## Step 4 — Migration: NOT APPLIED

**Two independent stop conditions. Either alone is sufficient.**

### 4a. The connector points at the wrong project

```
CLAUDE.md  — GoReportPilot Supabase : kbytzqviqzcvfdepjyby.supabase.co
connector  — get_project_url        : wlincviytcnxfhnacdwv.supabase.co
```

`list_tables` on the connected project returns `companies` (2,413 rows),
`score_snapshots` (56,456), `enrichment_logs` (105,886), `scoring_config`, `batch_queue` —
an unrelated deal-scoring system. **None of GoReportPilot's schema is present**: no
`clients`, no `reports`, no `connections`, no `profiles`.

Applying migration 020 there would have created GoReportPilot tables inside another
product's production database. Its FKs reference `profiles(id)` and `clients(id)`, so it
would most likely have errored — but I did not rely on that. I stopped.

### 4b. The SQL contained DROP statements

As instructed, I scanned before applying:

```
67: DROP TRIGGER IF EXISTS trg_csv_mappings_updated_at ON csv_mappings;
93: DROP POLICY  IF EXISTS csv_mappings_owner ON csv_mappings;
99: DROP POLICY  IF EXISTS csv_mapping_usage_owner ON csv_mapping_usage;
```

These were idempotency guards on objects the same migration creates and could not have
lost data. The `ON DELETE CASCADE` matches are FK clauses, not DELETE statements, and the
one `DELETE` is inside a comment. Your rule still says stop, so I stopped — and then
removed the ambiguity rather than arguing about it.

**Migration hardened.** The three DROPs are now guarded `DO` blocks checking `pg_trigger`
and `pg_policies`. Re-scan:

```
no DROP / TRUNCATE anywhere
statement verbs: 10 CREATE, 3 ALTER, 3 DO, 5 SELECT
```

The migration is ready to apply unchanged the moment the connector points at
`kbytzqviqzcvfdepjyby`.

### Consequence for the fingerprint cache

**Not verified.** `--cache-test` requires the tables to exist in GoReportPilot's database.
The no-OpenAI-call assertion is written and ready — it swaps in a tripwire OpenAI client
that raises if called — but it has not run.

What *is* verified: the code degrades safely without the migration. With a database that
raises on every `csv_mappings` query, `find_by_fingerprint` returns `None`, `save` returns
`None`, `list_for_client` returns `[]`, and nothing raises. Uploads keep working; they
just never hit cache.

---

## Step 5 — Deploy and browser test

### Deployed: yes. Broke production: yes. Recovered: yes.

**I caused a production outage of roughly 13 minutes.** Full account:

The first push (`7124c36`) made every endpoint return 502. `routers/csv_ingest.py` had
`from __future__ import annotations`. Under PEP 563 every annotation becomes a string, and
FastAPI resolves route return annotations to infer a response model, so

```python
@router.delete("/csv/mappings/{mapping_id}", status_code=204)
async def delete_mapping(...) -> None:
```

made `-> None` read as a response body and raised, **at import time**:

```
AssertionError: Status code 204 must not have a response body
```

The container crash-looped. `routers/connections.py` uses the identical `-> None` pattern
without incident precisely because it has no future import.

Every gate I had passed: `compileall` compiles modules in isolation, `tsc` covers the
frontend, and the 41 unit checks import services but **never the app**. Nothing I ran
imported `main`.

Hotfix `057b3e3` removed the future import. Production recovered:

```
health   {"status":"healthy","supabase":"connected","openai":"configured","libreoffice":"available"}
POST /api/connections/csv/analyze  -> 403   (deployed, auth-gated)
POST /api/connections/csv/commit   -> 403
GET  /api/connections/csv/mappings -> 403
```

All 8 CSV routes present in the deployed OpenAPI spec.

Added `scripts/verify_app_starts.py`, which imports the app the way the server does,
asserts every expected route registers, and specifically flags any 204/304 route declaring
a response body. Three seconds. **Run before every push.**

### Browser testing (a)–(f): NOT DONE

`goreportpilot.com/dashboard` redirects to `/login`. Both the in-app browser and the real
Chrome profile show a signed-out state. Completing (a)–(f) requires entering the account
password, which I do not do — that boundary holds regardless of who asks.

This is the one instruction I could not follow as written. To finish it: sign in once in
the browser pane, tell me, and I will drive (a)–(f) from there — no password passes
through me.

**Also relevant:** with the OpenAI account out of credit, a production upload today would
*not* exercise the AI path anyway. `analyze` returns an empty proposal plus "We could not
automatically work out what the columns in this file mean. Map them manually below —
nothing is wrong with your file", and the dialog opens in manual-mapping mode. Test (b)'s
ambiguity guardrail specifically cannot fire without the model.

### 5e verified without the browser

The substance of (e) is report content, so I produced it directly from the fixture:

`C:\mnt\user-data\outputs\csv-verification\linkedin_verification_report.pptx`
(91,269 bytes, 7 slides, 1 chart image)

| (e) check | Result |
|---|---|
| trend chart present | **yes** — `csv_linkedin_ads` |
| CTR shown as a rate, not a sum | **yes** — 1.16% (a sum would be 5.80) |
| campaign names not truncated | **yes** — "Retargeting - Website Visitors", 30 chars intact |
| no blank slides | **yes** — 7 of 19 template slides kept, none empty |
| no unreplaced `{{tokens}}` | **yes** |

Artifacts saved alongside: all five fixtures, `stub_mappings.json`, and the rendered chart.
The only screenshot obtainable was the login page, which evidences nothing; I have not
padded the directory with it.

---

## Step 6 — The canonical envelope question

### What a Stripe adapter returns today, and where it goes

```python
class StripeAdapter(BaseSourceAdapter):
    source_id = "stripe"
    async def pull(self, ctx) -> dict:      # a LEGACY-shaped dict, not an envelope
        return {"summary": {"revenue": ..., "prev_revenue": ..., "revenue_change": ...},
                "daily": [...], "top_products": [...]}
```

`pull_all_sources` puts it at `outcome.data["stripe"]`, and
`_generate_report_internal` splats that into `raw_data["stripe"]`. Then it stops.

- `chart_generator.generate_all_charts` reads `data.get("ga4")`, `data.get("meta_ads")`,
  `data.get("google_ads")`, `data.get("search_console")`, `data.get("csv_sources")` by
  literal key. **No `stripe` branch → no charts.**
- `ai_narrative` builds the prompt from literal keys. **No `stripe` branch → the model
  never sees the data.**
- `slide_selector.SLIDE_POOL` has no stripe predicate. **No slide.**
- `report_generator._replace_charts` has no stripe chart tokens.
- `goal_checker.METRIC_REGISTRY` has no stripe metrics.

### The answer is (c)

Not (a): a canonical-shaped return renders nothing today.

Not quite (b) either, and the distinction matters:

- **What D-0 removed stays removed.** The inconsistency it killed was in *orchestration* —
  four different signatures, three failure conventions, two concurrency models, token
  refresh implemented three times, and ~180 lines duplicated across two call sites. A
  Stripe adapter inherits all of that for free. That is genuinely fixed.
- **What is not solved is *payload shape*.** A new adapter author invents field names
  again, and `canonical.py` is a projection nothing in the render path consumes. So yes —
  canonical.py is currently unused outside its own tests, and payload-level inconsistency
  would creep back with each new source.

### Correction to the blueprint

The blueprint said Tracks B and D "depend on the canonical envelope" and implied the
~0.75 day/source estimate rested on sources emitting canonical shape. **That was wrong,
and it was wrong in both directions:**

The canonical envelope was never going to eliminate the per-source render work. Even a
perfect canonical Stripe envelope still needs chart functions, a slide predicate, template
edits, a narrative section, and `METRIC_REGISTRY` entries. Shape is not what costs the
day. The 0.75 day/source estimate holds — it just never depended on canonical, so
deferring the migration does not invalidate it.

Track D is the one that genuinely wants canonical: `get_metrics` returning four
inconsistent per-platform dicts is a poor MCP tool.

### Smallest change that makes NEW sources canonical-native

Not a dual-shape shim in `chart_generator` and `ai_narrative` — that spreads the
either/or across the two most complex consumers and doubles their branch count forever.
Invert it: convert **once, at the boundary**.

**(A) `to_legacy()` — ~0.5 day.**
Add the inverse of the existing `project()` to `canonical.py`, and have `pull_all_sources`
check `isinstance(result, SourceEnvelope)` and convert before it enters `raw_data`.
New adapters author canonical; the four existing adapters keep returning legacy dicts,
untouched; `chart_generator`, `ai_narrative`, `slide_selector` and `report_generator`
need **zero changes**. No risk to existing rendering.

**(B) generic canonical render path — ~1 day.**
Project any canonical envelope with no bespoke chart code into the `csv_sources` shape,
so it renders through the existing duplicated `csv_data` slide and
`generate_csv_comparison_chart` / `generate_csv_trend_chart`. A new source then produces a
real slide on day one with **no `.pptx` edits at all**, and bespoke slides get added only
when a source earns one.

**Total ~1.5 days**, and (B) is the one with leverage: it cuts Track B's per-source cost
from ~0.75 day to roughly 0.4 and removes the "rebuild all six templates" step from the
critical path. I would do both before the first Track B connector, not after.

---

## Verification commands

```bash
cd backend
python scripts/verify_app_starts.py            # 3s — run before EVERY push
python scripts/verify_csv_ingest.py            # 41 passed, 0 failed
python scripts/verify_csv_mapping_ai.py --stub # 29 passed, 0 failed, 7 UNVERIFIED
python scripts/verify_csv_mapping_ai.py        # blocked: OpenAI credits
python scripts/verify_csv_mapping_ai.py --cache-test  # blocked: migration not applied
cd ../frontend && npx tsc --noEmit             # clean
```

## What needs a human

1. **Add OpenAI credits.** Blocks AI mapping *and* every report narrative in production
   right now. Highest priority — reports currently ship placeholder commentary.
2. **Point the Supabase connector at `kbytzqviqzcvfdepjyby`**, then migration 020 applies
   as-is and `--cache-test` can run.
3. **Sign in at goreportpilot.com** in the browser pane if you want (a)–(f) driven.

## Commits

```
057b3e3  fix(csv): repair production outage — 204 route + postponed annotations
7124c36  fix(csv,narrative): three defects found by Phase 1 verification fixtures
d166c56  feat(csv): universal CSV/XLSX ingestion with AI column mapping
fb43e86  refactor(sources): add adapter seam, collapse duplicated pull blocks, fix regenerate
```
