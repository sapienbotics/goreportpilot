# Meta CSV — three fixes and a methodology change

Date: 2026-08-23
Commit: `97988f0`

All four items done. The most serious defect on the previous deck was the one
you identified as such: reach was being summed.

---

## You were right about the interim heuristic

I proposed "a ratio-unit value above 1 is a multiplier" as a cheap interim.
It is wrong, and the counter-example is on the deck I attached: Retargeting's
CTR is **4.12%**, and the account CTR scales to **1.07** — both above 1. That
heuristic would have rendered a real percentage as "4.12×". Same defect,
opposite direction, and it would have been harder to spot because it only
misfires on high-CTR campaigns.

The distinction is a property of the metric, not of its value, so no value
inspection can recover it. Scrapped; done properly below.

---

## 2. Deduplicated metrics (taken first — highest priority)

### The problem, measured

The old deck showed **REACH 5,186,231**. The largest single day in the file is
**101,502**. Summing 31 days of a people-count overstated the month by roughly
**51×** on this fixture — far past the 2–3× you estimated, because each of four
campaigns contributes its own daily row.

Worse than a wrong number in the general case: it is a number the client can
look up in their own Ads Manager and find wrong, which costs the agency
credibility rather than just accuracy.

### The fix

`MetricSpec.deduplicated` in the registry. Carried by `reach`,
`unique_clicks`, `unique_link_clicks`, `unique_users`, `users`. Such a metric
takes the **peak row** instead of the sum whenever more than one row is
involved — for the period totals and for each entity in the breakdown alike,
since they go through the same `aggregate()`. A single-row upload still sums,
because there is nothing to double-count.

### (b) peak-and-relabel — and why

**Chose (b).** The relabelling is clean: "Reach" → "Peak daily reach", which
is accurate, unambiguous, and reads naturally on a slide. Three reasons it
beats suppression here:

1. The number stays **real and checkable** — the client can verify peak daily
   reach against Ads Manager for that day and find it agrees.
2. Reach is the first thing a Meta advertiser looks for. Suppressing it leaves
   a hole on the one slide they care most about and invites "why is reach
   missing?" rather than answering anything.
3. Suppression would replace a checkable number with nothing, which is a
   worse trade than replacing a wrong number with a narrower true one.

The label change is the whole safeguard, so it is applied at the source rather
than left to the template: `_peak_daily_label()` in the normaliser, and the
source carries a warning saying exactly what happened.

### Frequency

**Suppressed**, not re-based. Impressions ÷ summed-reach divides by a number
that means nothing; and peak-day frequency would be a *different metric
wearing the same label*, which is the failure mode this whole exercise has
been about. There is no honest period frequency computable from daily rows, so
the deck says nothing rather than something plausible.

The rule is general, not a special case: any rate whose **denominator** is a
deduplicated metric is withheld over a multi-row set.

Warnings now attached to the source:

> - Peak daily reach is the highest single day, not a period total — deduplicated people-count; summing would double-count anyone reached on more than one day.
> - Frequency is not shown: needs reach, which is deduplicated and has no meaningful multi-day total.

### Native Meta OAuth path — checked, unaffected

You asked whether the API path has the same problem. **It does not**, for two
independent reasons:

- It never requests `reach` at all. The field list is
  `spend,impressions,clicks,ctr,cpc,cpm,actions,cost_per_action_type,purchase_roas`.
- Its summary comes from a **single account-level call over the whole period**,
  which Meta deduplicates server-side — not from summing the daily rows. The
  daily call (`time_increment: 1`) requests only `spend,impressions,clicks,
  actions`, all of which are genuinely additive.

So the correct pattern was already in place natively and only the CSV path
diverged. Worth noting for whenever reach *is* added there: adding it to the
account-level call stays safe; adding it to the daily call and summing would
reproduce this exactly.

---

## 1. Display units

`MetricSpec.display` is now mandatory and declared per metric, with the
import-time check refusing to load a registry entry that lacks a valid one —
the same pattern as the derivation check.

| Metric | Display | Renders |
|---|---|---|
| `frequency` | multiplier | `1.33×` |
| `roas` | multiplier | `3.52×` |
| `ctr`, `conversion_rate` | percent | `1.07%` |
| `cpc`, `cpm`, `cost_per_conversion`, `cost_per_lead`, `aov`, `spend`, `revenue` | currency | `$46,956.26` |
| `impressions`, `clicks`, `conversions`, `leads`, `sessions`, `reach`, and the unique-counts | number | `74,372` |

Every metric that could previously reach the `ratio` unit is now declared
explicitly. The mapper's inferred unit survives only as a fallback for metrics
the registry has never heard of.

Rendering is handled in three places that all needed it — `_fmt_csv_value`
(the CSV KPI slide), `select_kpis` (the generic scorecard), and `_unit_suffix`
(the AI narrative prose) — so a multiplier cannot pick up a `%` on any path.

This also brings the CSV path into line with the **native** path, which
already rendered ROAS as `f"{roas:.1f}x"`. The two now agree.

---

## 3. Entity level

`_coarsest_entity()` in `mapper._finalise`. When a file offers more than one
level of an ad-platform hierarchy, the coarsest wins — campaign > ad set > ad.
Deterministic, decided from measurement, same principle as finding B.

Guarded so it only acts on real hierarchies: a column named `Keyword` or
`Landing page` is left exactly as the model chose it, and a "coarser" column
with *more* distinct values than the finer one is rejected as a lying header.

Across five live runs: **5/5 `Campaign name`** (was 2/5).

---

## 4. Multi-run verification — and what it found

`verify_csv_mapping_ai.py --runs 5`. Every assertion runs N times and is
judged by its distribution: N/N passes, anything less is **UNSTABLE** and
fails the suite. Both `check()` and `check_model()` are measured, because
deterministic code consuming model output is only as stable as that output —
one of those varying would itself be a finding.

Assertion keys are **scoped by fixture**. My first version keyed on name
alone, which silently collapsed 37 assertions into 32, because several
fixtures share names like "low-confidence mappings are flagged" — a failure in
one file would have hidden inside passes from the other four.

I also added a **Meta CSV fixture** to that suite. It covers the date pair,
the `(USD)` header, em-dash nulls, dedup handling and display units. Without
it I would have been reporting "nothing unstable" from a suite that excluded
the one file where instability was actually observed, which proves nothing.

### Which assertions are unstable

**None — 52 assertions × 5 runs, 0 unstable, 0 failed.**

That number only means something because the harness was mutation-tested.
Disabling the date-column fallback makes it report:

```
51 passed, 0 failed, 1 UNSTABLE   (each assertion run 5x)
  UNSTABLE - passed on some runs and not others.
    3/5  [meta_csv] a date column is resolved on every run   [derived from model output]
           e.g. None
```

and exit 1. So the suite can see instability, and currently there is none —
because the two unstable behaviours were settled deterministically rather than
prompted around.

Cost note: a full run is now ~30 GPT-4.1 calls rather than ~6. `--runs 1`
remains available for a quick check, and prints "single run - proves possible,
not reliable" so nobody mistakes it for the real verdict.

---

## Rendered output — read from the deck

`NorthwindHome_July2026_MetaAds_FIXED.pptx`, read back by shape geometry:

| Slot | Label (rendered) | Value (rendered) |
|---|---|---|
| 0 | RESULTS | `3,240` |
| 1 | **PEAK DAILY REACH** | **`101,502`** |
| 2 | IMPRESSIONS | `6,921,544` |
| 3 | AMOUNT SPENT | `$46,956.26` |
| 4 | LINK CLICKS | `74,372` |
| 5 | CTR (LINK CLICK-THROUGH RATE) | `1.07%` |

Checked against the whole deck's text:

- `5,186,231` (the summed reach) — **absent**
- `1.33%` (frequency as a percentage) — **absent**
- FREQUENCY no longer occupies a slot; CTR moved up into it, so no blank card

Multiplier rendering verified directly, since frequency is suppressed in this
deck and would not otherwise be exercised: `3.52 multiplier → 3.52×`,
`1.3346 multiplier → 1.33×`, against `1.0745 percent → 1.07%`.

---

## Verification summary

| Suite | Result |
|---|---|
| `verify_app_starts.py` | pass — run before every push |
| `verify_csv_ingest.py` | 44 passed, 0 failed |
| `verify_csv_rendered_values.py` | 23 passed, 0 failed |
| `verify_csv_mapping_ai.py --runs 5` | **52 passed, 0 failed, 0 unstable** |

Every suite's output was line-accounted (`total = noise + report`) before I
drew a conclusion, per rule 14.

## CLAUDE.md

Rule 15 added: assertions on model output must be verified across multiple
runs; a single passing run proves the output possible, not reliable. It also
records the preference for settling instability deterministically — the
profiler has usually already measured what the model was guessing at — over
re-prompting until a run looks good.

---

## Process note

While mutation-testing the harness I needed to disable the date-column
fallback and put it back. I copied `mapper.py` to the scratchpad first and
restored from that copy, per rule 13 — the file had uncommitted work on it,
and this is the same situation where I previously used `git checkout` and
destroyed a session's changes.

## Still open, as agreed

- **Finding D / tech-debt 9** — no `{{csv_kpi_N_change}}` placeholder in the
  six templates.
- **Finding F / tech-debt 11** — `_parse_localized` printing to stdout (3,805
  lines of noise in the 5-run verification).
- **Tech-debt 1 and 2** — comments polling, httpx stderr logging.
