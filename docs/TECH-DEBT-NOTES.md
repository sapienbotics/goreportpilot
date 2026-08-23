# Tech Debt Notes

Log of known issues observed during verification work, not yet fixed.
Add to this file rather than fixing inline when the fix is out of scope
for the task at hand — see CLAUDE.md's "flag before fixing" process.

**Status:** items 3, 4, 5, 6 and 7 are fixed (see `PHASE-1-FIX-REPORT.md` and
`PHASE-1-CLOSE-REPORT.md`); their entries are kept below as the record of what
was wrong and how it was found. **Items 1, 2, 9 and 11 remain open.**

---

## 2026-08-23 — Phase 1 Pass 4 verification

### 1. `/api/comments/unread` polling frequency
Polls roughly every 6 seconds per open dashboard tab, and each poll makes
3 separate Supabase round trips. That's ~30 calls/minute per open tab.
Fine at current scale; will become a real load/cost problem around
~50 concurrently active users. Consider: longer interval, a single combined
query instead of 3, or moving to realtime/websocket push instead of polling.

### 2. httpx INFO-level logs going to stderr
Routine outbound HTTP requests (httpx's own request logging) are logged at
INFO level but land on stderr, which Railway's log viewer tags as `[error]`.
This means every normal HTTP call shows as an error in production logs,
burying real errors in noise. Root cause worth checking: either httpx's
logger is misconfigured to write to stderr, or Railway is tagging all
stderr output as error-level regardless of the Python log level. Fix
should target whichever is true — don't just silence the logger without
checking that real errors won't also get lost.

This directly affected debugging in Pass 4: diagnosing the `is_internal`
production discrepancy required adding a temporary diagnostic endpoint
because the underlying exception (once identified) would have been just
another line lost in this noise.

### 3. CSV import: source currency not read from the file — FIXED 2026-08-23
`services/csv_ingest/normalizer.py` / the report generator do not read a
CSV's stated currency (e.g. a "Currency: USD" line in an export's preamble,
or a `$` vs `₹` symbol in the raw cells) — monetary CSV metrics are always
rendered with the account's/platform's default currency symbol regardless
of what currency the source file is actually in. Confirmed on the LinkedIn
Ads fixture (`backend/tests/fixtures/csv_ingest/linkedin_ads_campaign_performance_july2026.csv`,
whose preamble states "Currency: USD"): the generated report showed
"₹107,135" for what is actually $107,134.97. Not a display-only glitch —
the number is numerically right, the currency label is wrong, which is
worse for an agency showing this to a client than a clearly-broken number
would be.

### 4. CSV entity breakdown: rate metrics summed instead of recomputed — FIXED 2026-08-23
`_build_entity_breakdown()` in `services/csv_ingest/normalizer.py` (line
~460) sums every mapped column per entity, including rate-type metrics
(CTR, conversion rate, CPC, CPM, cost-per-conversion) that must be
recomputed as a ratio per entity, not summed across that entity's rows.
Confirmed directly against the LinkedIn fixture: per-campaign CTR came out
as high as 71.4% and per-campaign conversion rate as high as 178.8% —
both mathematically impossible for a rate. The top-level aggregate metrics
(`_aggregate()`) do this correctly via an `average=` flag driven by
`_is_rate()`; `_build_entity_breakdown()` has no equivalent guard.

Currently dormant, not yet user-visible: nothing in `report_generator.py`,
the frontend, or the PPTX templates renders `breakdown`'s numeric fields
today — only entity *names* are read (`services/ai_narrative.py:198-200`,
for the "Top entries" list handed to GPT-4.1). The moment any per-entity
table or chart is built from `breakdown`, this will show broken numbers.
Worth fixing before that feature lands, not after.

### 5. CSV report KPI headline shows only the latter half of the period — FIXED 2026-08-23
For a single dated CSV source, `normalize()` splits the uploaded rows at
the date midpoint into "previous" and "current" halves so the report can
show period-over-period change (see `normalizer.py:186-199`). The KPI
cards and PPTX slide for that source then display only `current_value`
(the second half) as the headline number, with a `change` badge versus
the first half. The full-period total (both halves summed) is never shown
as a single number anywhere in the deck — confirmed on the LinkedIn
fixture: the report showed "2,053,132" impressions (second-half-of-July
only) with a "+12.1%" badge, never "3,884,961" (the true July total),
though the trend chart below it does correctly plot the full date range.
This may be intentional (trend framing over raw total), but it's worth a
deliberate product decision rather than being an implicit side effect of
the comparison-split logic — a user skimming just the headline number
will materially undercount their own period's performance.

### 6. AI narrative attributes aggregate changes to specific entities — FIXED 2026-08-23
`services/ai_narrative.py` passes GPT-4.1 only entity *names* from a CSV's
`breakdown` (top 5 by primary metric, see item 4's line reference), not
each entity's own trend. The model is separately given the aggregate
period-over-period change for each metric ("impressions: X, change:
+12.1%"). Observed on the LinkedIn fixture: the model attributed the
overall +12.1% impressions increase specifically to campaign "Q3 Thought
Leadership | Video Views" and the overall +15.9% conversions increase to
"Q3 Lead Gen Form | Agency Owners" — but recomputing each campaign's own
first-half-vs-second-half change directly from the source rows shows
Video Views actually grew only +3.5% in impressions (Demand Gen +34.6%
and Lead Gen +33.0% were the real drivers), and Lead Gen Form's own
conversions grew +35.6% (not +15.9%, which is the all-campaign aggregate).
The model isn't fabricating numbers — the +12.1%/+15.9% figures it cites
are real — but it is pinning a whole-source aggregate change onto one
named entity it has no trend data to actually attribute it to. Fix is
either to stop naming a specific entity next to an aggregate change in
the prompt instructions, or to give the model real per-entity trend data
(from `breakdown`, once item 4 is fixed) so an attribution claim like this
would be grounded.

### 7. CSV mapping confidence exactly at the threshold slips through — FIXED 2026-08-23
`ColumnMapping.needs_confirmation` is `confidence < CONFIDENCE_THRESHOLD`
with the threshold at 0.80, so a model returning exactly `0.80` is treated
as pre-accepted and raises no confirmation prompt. Observed on 2026-08-23:
`scripts/verify_csv_mapping_ai.py` failed its two "'Cost' is questioned
rather than silently mapped" assertions because that run's live GPT-4.1
returned `confidence=0.8` with no ambiguity, where earlier runs returned a
lower value plus an ambiguity. Not caused by any code change — `mapper.py`
was untouched — but it means that test is flaky at the boundary, and more
importantly that a genuinely borderline column can reach a client report
without anyone being asked. Worth deciding whether the comparison should be
`<=`, and separately whether that verification script should assert on a
model-judgment value at all (see CLAUDE.md rule 12's concern about
assertions that measure something adjacent to the claim).

---

## 2026-08-23 — Meta Ads CSV verification

### 8. "ratio" unit renders as a percentage — FIXED 2026-08-23
`_slide_unit()` in `services/csv_ingest/normalizer.py` collapses the mapping
unit "ratio" onto "percent", and `_fmt_csv_value()` then appends a "%". That is
right for a CTR expressed as 0.0047, and wrong for a ratio that is a
multiplier. Meta's **Frequency** is impressions per person — 1.33 means each
reached person saw the ad 1.33 times — and the deck renders it "1.33%", which
is not a quantity that exists. Confirmed on the rendered KPI slide of
`meta_ads_export_july2026.csv`. **ROAS has the same shape** (a 3.5x return
would render "3.5%") and so would any "X per Y" multiplier.

The value is correct; only the suffix is wrong, which is the more dangerous
kind of error because nothing looks broken. Fix is a fourth display unit —
"multiplier", rendered as a bare number or with an "x" — distinguished from
"percent" at mapping time. `MetricUnit` in `schema.py` would need the new
member and the mapper prompt would need to know when to choose it; a cheaper
interim is to treat a ratio-unit metric whose value exceeds 1 as a multiplier,
since a genuine percentage stored as a fraction is by definition <= 1 after
`_percent_scale` has run.

Not fixed: flagged rather than changed, because it alters rendering for every
existing ratio metric and deserves an explicit decision.

### 9. No template has a `{{csv_kpi_N_change}}` placeholder
All six PPTX templates carry only `label` and `value` tokens for CSV KPI
cards. `_populate_csv_slide()` computes `change_str` — including the explicit
`change` field added when the full-period headline landed — and then has
nowhere to put it, so the within-period trend never appears on a CSV source
slide. The number is computed, reaches the AI narrative (where it is used
correctly), and is silently dropped at render time.

Consequence after the generic-KPI-slide suppression (item 4a of the Meta
verification): a CSV-only deck now shows no change indicator on any KPI card
at all. This is not a regression — the generic slide previously showed "—" for
these metrics, because `previous_value` is None for a single upload — but it
does mean the trend lives only in the narrative and the trend chart.

Fixing it means editing six binary .pptx files to add a third text box per KPI
card, which is a template-design task rather than a code change.

### 10. Entity column unstable under a hierarchy — FIXED 2026-08-23
Across five live GPT-4.1 runs on the same Meta export, the model chose
"Campaign name" twice and "Ad name" three times as the entity column. Both are
defensible readings and the numbers are correct either way, but the report's
"top entries" change identity between runs of the same file, and a saved
mapping therefore locks in whichever level happened to win. Worth deciding
whether the mapper should prefer the coarsest hierarchy level by default, or
whether this should become an explicit ambiguity question ("report by campaign,
ad set, or ad?") the way the Cost column already is.

### 11. `_parse_localized` prints to stdout on every failed parse
`services/csv_ingest/profiler.py` emits `Could not parse numeric value: ...`
via `print()` for each cell it probes and rejects — which is normal, expected
behaviour while inferring column types. A single verification run produced 529
such lines against 59 lines of actual report, and the CSV ingest suite 202
against 65. In production this goes to stdout on every upload and lands in
Railway's logs, compounding item 2's noise problem. It also actively obstructs
CLAUDE.md rule 14 (read all of a command's output) by burying the signal.
Should be `logger.debug()`, not `print()`.
