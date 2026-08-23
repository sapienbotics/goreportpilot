# Peak-daily-reach trend framing — fix report

Date: 2026-08-23
Commit: `17bdab1`

Fixed generally, not for reach specifically. Took three attempts to fully
close, and the last two of those attempts were only judged insufficient by
running the live model repeatedly and, at the end, by reading the complete
rendered deck rather than a suite's pass/fail count.

---

## The defect

The previous deck read: *"Peak daily reach fell by 14.4% (101,502 to
86,913); expand audience pools or adjust frequency caps."*

Peak daily reach is a maximum, not a sum. Comparing the highest day of one
half of the period against the highest day of the other half is two order
statistics, not a trend — a single strong day early in July can manufacture
a "decline" that never happened. Both endpoints were individually *correct
numbers*; the defect was treating the pair as comparable at all, which is
exactly what let it survive the earlier reach-summing fix (that fix made the
*value* honest; it never touched the *comparison*).

---

## The general fix (structural)

`derivations.is_deduplicated(key)` now suppresses `change`,
`first_half_value`, and `second_half_value` — never computed, not computed
and hidden — wherever a metric is reduced:

- **Period totals**, in `normalize()`.
- **Per-entity breakdown**, in `_build_entity_breakdown()`, which had the
  identical bug one level down: an entity's own peak day compared against
  its own other-half peak day. Verified directly: `no entity's reach carries
  a change either` — passing on every run.

Generalized past reach specifically, per your instruction to cover the
class: a rate derivation with a deduplicated component on **either side**
(not just the denominator, the only case the earlier fix handled) is now
suppressed the same way — so a future metric shaped the other way round
(deduplicated numerator instead of denominator) doesn't need its own
special case.

A warning is attached to the source explaining the omission, matching the
existing pattern for the value itself: *"Peak daily reach has no
period-over-period comparison: it is a peak value, not a sum, so comparing
two maxima would manufacture a trend from a single strong or weak day rather
than measuring one."*

---

## The narrative fix — three attempts, verified live each time

Every attempt was checked against the real model at `--runs 5` before being
judged sufficient or not, per CLAUDE.md rule 15. The first two were not.

### Attempt 1: supply the real value, forbid the framing

Gave the model reach's actual peak value at both source and entity level,
each with an explicit *"do not describe it as rising, falling, or
trending"* instruction.

**Live result: FAILED, 5/5 or 3/5 across two runs.** The model substituted a
*different* metric's real change for reach's: *"Video Views ... delivered
2.2% fewer link clicks and **2.0% less reach**"* — 2.0% was that entity's
real impressions change, relabelled. Root cause: `reach` wasn't even in the
per-entity metric priority list, so the model had a real number sitting
next to reach in the prompt (impressions) and no real number for reach
itself — and reached for the neighbor.

### Attempt 2: withhold the topic entirely

Removed reach from every prompt line — source-wide and per-entity — leaving
only a single blanket notice: *"Peak daily reach is shown only as a number
on the slide and excluded from this analysis... do not mention, estimate,
or describe it in any section."*

**Live result: UNSTABLE, 3/5.** The model used ordinary marketing
vocabulary with **zero numeric grounding**: *"reach and engagement
improved"*, *"regain lost reach"*, *"expanded reach and clicks among new
audiences"* — that last one inside a `chart_insights` **caption**, which
renders directly on a slide as a chart title and which neither attempt's
scope had reached. "Reach" is common enough English that an instruction not
to use it is not a reliable constraint on a language model.

### Attempt 3: deterministic scrub (the one that holds)

Two rounds of prompt engineering not converging is the signal your rule 15
exists to produce: *prefer settling it deterministically over re-prompting
until a run looks clean.* `generate_narrative()` now runs every section,
every list item, and every `chart_insights` caption through a scrub before
returning — sentence-level removal of any sentence whose clause pairs a
withheld subject with a percentage or trend word.

**Live result at the time: 55 passed, 0 failed.** The scrub log from that
run:

```
Narrative scrub removed 3 sentence(s) ungroundedly describing reach as trending
Narrative scrub removed 3 sentence(s) ungroundedly describing reach as trending
Narrative scrub removed 1 sentence(s) ungroundedly describing reach as trending
Narrative scrub removed 3 sentence(s) ungroundedly describing reach as trending
```

**The underlying model tendency did not go away — it fired on 4 of the 5
runs, same as before. Shipping it did.** That is the actual claim being
made here: not that the model was fixed, but that the pipeline now
guarantees the invariant regardless of the model's day-to-day phrasing,
the same way the date-column and entity-hierarchy fixes from the prior pass
replaced unreliable model judgment with deterministic code.

---

## Two bugs in my own detector, found only by reading the final deck

The `--runs 5` suite reported 0 failed at this point. I regenerated the
actual deck anyway and grepped every rendered sentence, per your explicit
instruction — and it still had a violation. Two bugs in the detector
itself, neither of which the suite's five live samples happened to
exercise:

**1. Word list had the wrong verb form.** `TREND_WORDS` had `"expanded"` and
`"expanding"` but not the bare present-tense `"expands"`. The final deck
read: *"...optimize ad creatives to maintain engagement as **reach
expands**."* — this exact sentence reached slide 3 while the suite reported
a clean pass, because none of the five live narrative generations in that
run happened to phrase it in the missing conjugation.

Rewrote the list to *generate* regular-verb conjugations (bare/-s/-ed/-ing)
from a base-verb list rather than hand-listing forms one at a time — hand-
listing is exactly how this gap was created, and would keep recreating
gaps indefinitely.

**2. The clause splitter broke on thousands separators.** It split on
*every* comma, including the one inside `1,021`. In *"Post comments dropped
1.9% (1,021 to 1,002) despite higher reach"*, that split the number apart,
severing `1.9%` from `reach` even though both are in the same real clause —
a false negative. Fixed: don't split on a comma immediately followed by a
digit.

Both fixes were verified against an 11-case regression panel (the four
original bugs, both new bugs, and three deliberately-safe sentences
including a real thousands-separated number with no trend attached) before
re-running the live suite, and again before the final deck regeneration.

---

## Verified: the definitive final deck

Regenerated after both detector fixes, with live GPT-4.1, full production
pipeline. Every occurrence of "reach" in the rendered `.pptx`:

```
[slide 3] PEAK DAILY REACH
```

That's the KPI card label — one word, a rendered number beside it, no free
text. **Zero occurrences anywhere in prose**: not in the executive summary,
not in key wins, not in concerns, not in next steps, not in
`csv_performance`, not in `chart_insights`. Confirmed by grepping both the
raw narrative dict (pre-render) and the actual `.pptx` text extracted via
python-pptx — two independent surfaces, same result.

`NorthwindHome_July2026_MetaAds_REACHFIX.pptx` attached. KPI slide (page 3)
still shows the correct values from the prior pass: `PEAK DAILY REACH
101,502`, no `5,186,231`, no `1.33%`.

---

## Verification summary

| Check | Result |
|---|---|
| `verify_app_starts.py` | pass — run before every push |
| `verify_csv_ingest.py` | 44 passed, 0 failed |
| `verify_csv_rendered_values.py` | 23 passed, 0 failed |
| `verify_csv_mapping_ai.py --runs 5` | **55 passed, 0 failed, 0 unstable** |
| Final deck, live regeneration, full grep | **0 occurrences of "reach" outside the KPI label** |

New deterministic assertions (run every time, not just `check_model`):
*"reach carries no period-over-period change"*, *"no entity's reach carries
a change either"*. New model-facing assertion at `--runs 5`: *"narrative
never frames peak daily reach as rising, falling, or trending."*

`sentence_claims_trend`, `TREND_WORDS`, and the clause splitter now live
once, in `services/ai_narrative.py` — the module that scrubs the production
narrative with them — and `verify_csv_mapping_ai.py` imports rather than
duplicates. Two independent copies of the same heuristic drifting apart is
exactly the failure mode that produced the earlier `<` vs `<=` threshold
bug; not repeating it here.
