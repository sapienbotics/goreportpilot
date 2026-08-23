# Phase 1 Fix Report — rendered values

Date: 2026-08-23
Commit: `d46058f`

Fixes the ratio-metric defect found on slide 6 of the Pass 4 deck, plus
tech-debt items 5 (half-period headline) and 3 (source currency). Items 1, 2
and 6 deliberately untouched; item 6 is now unblocked, since it depended on
item 4 landing.

---

## Before / after — values actually rendered on the KPI slide

Both columns are read from a generated `.pptx`, not computed. The "before"
column is slide 6 of `videogenie_July2026_LinkedIn_Report.pptx` from Pass 4;
the "after" column is the deck this run produced, read back through
python-pptx by `scripts/verify_csv_rendered_values.py`.

| KPI | Before | After | Why it was wrong |
|---|---|---|---|
| IMPRESSIONS | 2,053,132 | **3,884,961** | headline was the period's second half |
| CLICKS | 14,318 | **27,011** | same |
| CLICK THROUGH RATE | 1.04% | **0.70%** | unweighted mean of per-row CTRs |
| AVERAGE CPC | ₹7.53 | **$7.38** | unweighted mean, and wrong currency |
| AVERAGE CPM | ₹73 | **$51.34** | unweighted mean, wrong currency, cents dropped |
| TOTAL SPENT | ₹107,135 | **$199,457.12** | half period, wrong currency, cents dropped |

Every "after" value matches the target you specified, within the stated
tolerances.

### On the CPM figure

Your finding quoted CPM as "correct: $52.18", while the verification spec you
gave asserted `51.34 (±0.1)`. Those are different numbers and I did not want
to silently pick one. $52.18 is what the mandated formula gives when applied
to the *second half only* — I reproduced it exactly during mutation testing
(below): with the half-period headline still in place but rates recomputed
from components, the deck renders `$52.18`. Over the whole July period,
Σspend / Σimpressions × 1000 = 199,457.12 / 3,884,961 × 1000 = **51.34**,
which is what your assertion spec expects. I implemented the full-period
figure, consistent with the headline fix.

### Per-entity rates (tech-debt item 4, fixed by construction)

| Campaign | CTR before | CTR after | Conv. rate before | after |
|---|---|---|---|---|
| Q3 Thought Leadership \| Video Views | 12.87% | 0.41% | 8.73% | 0.33% |
| Q3 Demand Gen \| Marketing Ops \| US | 17.79% | 0.58% | 56.22% | 1.86% |
| Q3 Lead Gen Form \| Agency Owners | 29.22% | 0.94% | 108.12% | 3.57% |
| Q3 Retargeting \| Website Visitors | 71.42% | 2.31% | 178.77% | 5.77% |

---

## The fix

### One registry, one derivation

New `backend/services/csv_ingest/derivations.py`. Every ratio metric declares
its numerator and denominator once:

```python
RATE_DERIVATIONS = {
    "ctr":                 RateDerivation("clicks",      "impressions", 100.0),
    "cpc":                 RateDerivation("spend",       "clicks"),
    "cpm":                 RateDerivation("spend",       "impressions", 1000.0),
    "conversion_rate":     RateDerivation("conversions", "clicks",      100.0),
    "cost_per_conversion": RateDerivation("spend",       "conversions"),
    "cost_per_lead":       RateDerivation("spend",       "leads"),
    "roas":                RateDerivation("revenue",     "spend"),
    "aov":                 RateDerivation("revenue",     "conversions"),
}
```

An import-time check refuses to load the module if an alias points at a rate
with no declared derivation, or if a derivation names a component with no
alias list. So a new rate metric cannot be added without saying how it
derives — the failure is at import, not on a client's slide.

Component names resolve through an alias table, because uploads disagree on
naming: the LinkedIn file calls spend `Total Spent`, the Semrush file maps
`Cost` to `ad_spend`, and both resolve to the same canonical `spend`. The
alias lists are deliberately tight — `reach` is not an impressions alias and
`sessions` is not a clicks alias, since a wrongly resolved component produces
exactly the class of wrong number this module exists to prevent.

`aggregate()` in that module is now the **only** place any metric is reduced
over a set of rows. Both `normalize()` (period totals) and
`_build_entity_breakdown()` (per-campaign) call it. They cannot drift apart
again, which is the substance of your "do not fix one and leave the other" —
item 4 is not fixed separately, it is the same function now.

### Fallback behaviour

- Both components present → recomputed exactly (`Σnum / Σden × scale`).
- Only the denominator present → weighted mean by that denominator. This is
  algebraically identical to recomputing, since `Σ(rateᵢ·denᵢ)/Σdenᵢ ==
  Σnumᵢ/Σdenᵢ` — exact, not an approximation.
- Neither → volume-weighted mean, weighting by the first available of
  impressions, clicks, sessions, users, conversions, spend; failing that, the
  largest non-rate column as a volume proxy. Never an unweighted mean unless
  no volume column exists at all, and that case is recorded as
  `unweighted_mean` so it is visible.
- Zero denominator → `None`. Not `0`, not `inf`. A metric whose value is
  `None` is omitted from the slide rather than rendered, because "no
  conversions this period" is not "a cost per conversion of zero".

**Which fixture metrics hit the fallback path: none.** All five rates in the
LinkedIn fixture (`ctr`, `cpc`, `cpm`, `conversion_rate`,
`cost_per_conversion`) recompute from components present in the upload. The
verification script prints the derivation method for every metric and asserts
that nothing fell back to an unweighted mean. For contrast, a Semrush-style
upload with `position` and `traffic_percent` and no components would take the
weighted-mean path; the `derivations` block now returned on every normalized
source records which path each metric took.

### Full-period headline (item 5)

`normalize()` still splits a dated upload at its midpoint, but only to compute
the change badge. The headline is the whole uploaded period. `previous_value`
is now `None` rather than the first half — leaving it would have made the
comparison chart draw a full-period bar against a half-period one — and
`change_basis: "within_period"` marks the badge as an internal trend, not
month-over-month. `first_half_value` / `second_half_value` are kept for the
narrative.

Three downstream consumers needed adjusting for `previous_value` being absent:
`_populate_csv_slide` now prefers the explicit `change` field instead of
re-deriving it (dividing a full period by a half period would have invented a
number ~+112%); `generate_csv_comparison_chart` skips a chart with nothing to
compare against rather than plotting `None`; and `ai_narrative` states
explicitly that the figure is a period total whose change is an internal
trend, so the model does not describe it as growth against a prior month.

### Source currency (item 3)

New `backend/services/csv_ingest/currency.py`, read in order of authority:
preamble line (`Currency: USD`), then money-column headers (`Total Spent
(USD)`), then cell symbols. Only columns actually mapped as money are
inspected, so a `$` in a campaign name cannot decide the report's currency.

Ambiguous symbols are deliberately *not* resolved: `$` alone could be USD,
CAD, AUD, SGD, HKD, MXN or BRL, so a bare `$` yields no detection and the
account default stands. Guessing a currency onto a correct number is worse
than admitting the file did not say.

Currency formatting now keeps cents whenever a value has them. The old rule
("2dp below 10, none above") rendered a CPM of 51.34 as `$51`; on a CPM or CPC
a third of a unit is a real difference. Whole amounts still render clean —
1,240,000.00 is `$1,240,000`, not `$1,240,000.00`.

---

## Verification

`backend/scripts/verify_csv_rendered_values.py` — 23 assertions, all passing.
It generates a real deck from the fixture and reads the text rendered onto the
CSV KPI slide.

Two design points worth stating, since the whole issue here was a verification
method that measured the wrong thing:

**The slide is located by geometry, not by its text.** My first version
matched the slide containing the word "IMPRESSIONS" — and picked the deck's
*generic* KPI scorecard, which also says "IMPRESSIONS". It then reported six
missing labels while the correct CSV slide sat beside it rendering all six
values perfectly. The regression guards passed at the same time, because the
wrong values genuinely were absent. That is the same failure mode as Pass 4 in
miniature: confident output from an assertion pointed at the wrong object.
Only the CSV slide carries shapes at the template's `csv_kpi` token
coordinates, so those coordinates now select it unambiguously, and the same
coordinates tie each rendered value back to its label.

**The account currency is set to INR in the test on purpose.** If per-source
currency were not genuinely winning, the deck would render `₹` and the
assertions would fail. A test with the account already on USD would pass
whether or not the feature worked.

### Mutation testing

A test that cannot fail proves nothing, so each assertion was checked by
reintroducing the bug it guards:

| Mutation | Result |
|---|---|
| Rates back to an unweighted mean | **caught** — CTR renders `1.06%`, CPC `$7.49`, CPM `$74.12` |
| Headline back to the half period | **caught** — impressions `2,053,132`, clicks `14,318`, spend `$107,134.97`, CPM `$52.18` |
| File currency ignored | **caught** — CPC `₹7.38`, CPM `₹51.34`, spend `₹199,457.12`, plus the currency-detection assertion |

The mutation run also exposed a real defect in the verification tool itself:
printing a failure detail containing `₹` raised `UnicodeEncodeError` on a
cp1252 console, turning a legible FAIL into a traceback. A verification tool
that crashes on the evidence it exists to surface is worse than useless, so
its stdout is now lossy rather than fatal.

### Existing suites

- `verify_csv_ingest.py` — 44 passed, 0 failed.
  Three assertions in `test_aggregation` encoded the old semantics and were
  rewritten. Its fixture was also **self-contradictory**: the CTR column said
  6.0% on days whose own clicks and impressions worked out to 5.0%, so summing,
  averaging and recomputing were indistinguishable and any method looked
  defensible. The fixture is now internally consistent and built so all three
  answers differ (summed 30.0, unweighted mean 5.0, correct 5.3333), and the
  test asserts the correct one *and* explicitly that the value is not the
  unweighted mean.
- `verify_app_starts.py` — passes; run before every push, as instructed.
- `verify_report.py`, `verify_chart_sizing.py` — pass.
- `verify_csv_mapping_ai.py` — **2 pre-existing failures, not caused by this
  change.** That run's live GPT-4.1 returned `confidence=0.8` for the `Cost`
  column with no ambiguity raised, where the test expects a question. Since
  `needs_confirmation` is `confidence < 0.80`, a model answering exactly at
  the threshold slips through unconfirmed. `mapper.py` is untouched by this
  work and imports nothing I changed. Logged as tech-debt item 7 rather than
  fixed — it is a threshold/product decision, not a regression.

### CLAUDE.md

Added rule 12: assertions on user-visible values must read the rendered
output, never a recomputation alongside the code under test.

---

## One process note

While mutation-testing the half-period headline I reverted the mutation with
`git checkout` on `normalizer.py` — a file with substantial uncommitted work
on it. That discarded all of it, not just the mutation line. I rebuilt the
file from context and re-verified (23/23 and 44/44 both green afterwards), and
the other eight changed files were untouched, so nothing was lost beyond the
time. Recording it because the correct move was a scratch copy, and because
"destructive command on uncommitted work" is the same class of mistake as the
sequencing incident earlier in this engagement.

---

## Not fixed this pass, as instructed

- **Item 1** — `/api/comments/unread` polling frequency.
- **Item 2** — httpx INFO logs on stderr showing as `[error]` in Railway.
- **Item 6** — narrative attributing aggregate changes to specific entities.
  Now unblocked: `breakdown` carries correct per-entity rates, so the model
  can be given real per-entity trend data instead of names alone.
- **Item 7** — new: confidence exactly at the 0.80 threshold is auto-accepted.
