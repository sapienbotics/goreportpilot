# Phase 1 Close Report

Date: 2026-08-23
Commits: `f712e6b`, `8006d35`, `5d8bf4b`

Items 1 (threshold boundary), 2 (live end-to-end deck) and 3 (narrative entity
attribution) complete. Tech-debt items 1 and 2 remain deferred as instructed.

`verify_app_starts.py` run before every push; all runs passed.

---

## Item 1 — threshold boundary

`needs_confirmation` changed from `confidence < 0.80` to `<= 0.80`, and the
mapper prompt updated to match — it previously told the model 0.8 meant
"confident" while the code was about to treat it as needing review.

**Both pre-existing failures in `verify_csv_mapping_ai.py` resolve.** Final:
**37 passed, 0 failed.**

### The audit found four more copies of the boundary

Checking for the same error elsewhere turned up the comparison duplicated in
five places, of which only the schema had been fixed:

| Location | Was | Now |
|---|---|---|
| `services/csv_ingest/schema.py:61` | `<` | `<=` (the real one) |
| `frontend/.../CSVMappingDialog.tsx:89` | `<` | `<=` |
| `frontend/.../CSVMappingDialog.tsx:465` | `<` | `<=` |
| `scripts/verify_csv_mapping_ai.py` ×3 | `<` | asks `needs_confirmation` |

The **frontend pair was a shipping bug**, not a tidiness issue. With the
backend at `<=` and the dialog at `<`, a column at exactly 0.80 leaves the
Confirm button enabled, and the commit endpoint — which gates on
`needs_confirmation` — then rejects it with a 422 the user cannot act on. That
would have reached production in this state.

The three test copies now ask `cost_mapping.needs_confirmation` rather than
re-deriving the comparison. One of them was still reporting a failure the code
had already fixed, which is the same anti-pattern CLAUDE.md rule 12 exists to
prevent, one layer up: the test re-implemented the logic instead of asserting
the property.

`services/csv_parser.py:164` (`chardet confidence >= 0.70`) was reviewed and
**left alone** — different shape: its result is validated by actually decoding
with a latin-1 fallback, and chardet emits continuous statistical floats
rather than round model-chosen numbers. Frontend typecheck clean.

---

## Item 2 — real end-to-end deck, live GPT-4.1

`/mnt/user-data/outputs/videogenie_July2026_LinkedIn_LIVE.pptx`. Generated
from the LinkedIn fixture with the real model, account currency deliberately
set to INR so the per-source currency handling is genuinely exercised.

### Does it describe the change as an internal trend, not prior-month growth?

**Yes.** Consistently: *"In the second half of the month, both conversions
(+20.0%) and cost efficiency (cost per conversion -2.5%) improved"*, and
*"Performance improved in the second half: conversions rose from 335 to 402
(+20.0%)"*. Nothing anywhere frames a figure as growth against June.

### Does the trend chart render?

**Yes** — confirmed visually (page 4, rendered via LibreOffice → PDF → PNG).
The impressions series spans Jul 01 → Aug 01 with the weekend dips intact,
below correct KPI values: 3,884,961 / 27,011 / 0.70% / $7.38 / $51.34 /
$199,457.12, all in dollars despite the INR account.

### Is the comparison chart absent, and is that intended?

**Absent, and intended.** `generate_all_charts` returned exactly one chart for
this source (`csv_linkedin_ads_campaign_performance_july2026.csv` — the trend
chart). The comparison chart plots current-vs-previous bars; with
`previous_value` now `None` there is no prior period to plot, so it returns
`None` rather than drawing a row of full bars beside a row of empty ones. The
time dimension is carried by the trend chart, which is the better instrument
for it. A file that genuinely carries its own prior period (the legacy
long-KPI templates) still populates `previous_value` and still gets the
comparison chart.

### Full narrative

**Executive Summary**
> Videogenie continued its focus on subscription growth in July, with LinkedIn
> Ads as the primary available channel. In the second half of the month, both
> conversions (+20.0%) and cost efficiency (cost per conversion -2.5%)
> improved, led by the 'Q3 Demand Gen | Marketing Ops | US' campaign which
> grew conversions by 37.3%. However, overall spend increased by 17.0% in the
> second half, and some campaigns like 'Q3 Thought Leadership | Video Views'
> still posted high costs per conversion despite modest conversion growth. The
> key challenge now is to accelerate subscription gains while tightening cost
> controls. Shifting more budget toward high-performing campaigns such as 'Q3
> Lead Gen Form | Agency Owners', which cut cost per conversion by 9.6%, will
> help maximize results as spend rises.

**Key Wins**
> - Q3 Demand Gen | Marketing Ops | US increased conversions by 37.3% in July.
> - Q3 Lead Gen Form | Agency Owners cut cost per conversion by 9.6% while raising conversions by 29.9%.
> - Q3 Thought Leadership | Video Views reduced cost per conversion by 11.9% despite flat click volume.

**Concerns**
> - Q3 Thought Leadership | Video Views posted a high cost per conversion ($1,475.73) despite only 22 conversions; pause or reallocate budget.
> - Q3 Retargeting | Website Visitors saw cost per conversion rise 1.6% to $89.64; review targeting and creative to improve efficiency.
> - Q3 Demand Gen | Marketing Ops | US increased average CPC by 2.4% to $8.57; test new ad copy and placements to lower costs.

**Next Steps**
> 1. Next month we will shift 15% of budget from 'Q3 Thought Leadership | Video Views' to 'Q3 Lead Gen Form | Agency Owners', based on cost per conversion ($1,475.73 vs $320.08), to drive at least 40 more conversions.
> 2. Next month we will refresh creative and audience segments on 'Q3 Retargeting | Website Visitors', based on the 1.6% rise in cost per conversion, to target a 10% efficiency gain.
> 3. Next month we will A/B test new ad copy for 'Q3 Demand Gen | Marketing Ops | US', based on the $8.57 average CPC, to reduce click costs by 10%.

*(CSV Performance, Website Performance and Paid Advertising sections omitted
here for length; the first is audited below, the latter two correctly report
GA4/Meta/Google data as unavailable.)*

---

## Item 3 — narrative entity attribution

The breakdown now carries each entity's own first-half-vs-second-half change,
and the prompt states that the source-wide change is not any single entity's
change.

### Every entity-attributed figure, audited against the source data

| Narrative claim | Entity's own data | ✓ |
|---|---|---|
| Demand Gen conversions +37.3% | +37.3% | ✓ |
| Lead Gen cost/conv −9.6%, conversions +29.9% | −9.6%, +29.9% | ✓ |
| Video Views cost/conv −11.9% | −11.9% | ✓ |
| Video Views $1,475.73, 22 conversions | 1,475.73, 22 | ✓ |
| Retargeting cost/conv +1.6% to $89.64 | +1.6%, 89.64 | ✓ |
| Demand Gen CPC +2.4% to $8.57 | +2.4%, 8.57 | ✓ |
| Lead Gen cost/conv $320.08 | 320.08 | ✓ |

No aggregate figure is attached to a named entity anywhere. The Pass 4 failure
— crediting Video Views with the account's +12.1% — does not recur.

### A prerequisite fix: the halves were not comparable across entities

Item 3 could not be built on the per-entity changes as they were computed:

- **The split was at the midpoint of the ROW list.** An entity-per-day export
  has several rows per date, so on this fixture (4 campaigns × 31 days) index
  62 landed *inside* 2026-07-16 — giving two campaigns 16 days "before" and 15
  "after" while the other two got the reverse. Every entity's change was
  measured over a different span than its neighbour's. Now split on a date
  boundary, so all entities share identical windows.
- **The windows are now equal in length.** An odd day count cannot be halved,
  so the middle day is excluded from the *comparison* while still counting in
  the period total, rather than landing on one side and inflating it. July
  compares 1st–15th against 17th–31st.

I treated this as inside item 3's scope rather than raising it separately,
because per-entity attribution is only meaningful if the per-entity numbers
are comparable — flagging it here prominently instead.

**This changes what the data says.** Under equal windows the Video Views
campaign is **−4.1% on impressions and −2.9% on clicks** — a genuine decline
that the unequal split had reported as +3.5% growth. Your original brief said
*"Video drifts down"*; my Pass 4 report recorded that as "could not be
confirmed", and it was wrong to. The hand-check I used to "verify" it had the
same unequal-window flaw as the code. The live narrative now flags Video Views
in Concerns, unprompted.

### Three further defects, found only by running the live model

None of these could have surfaced from the synthetic deck — they are exactly
what item 2 existed to catch.

**1. The model invented absolute half-period values.** Given only a total and
a percentage, the first live run wrote *"conversions rising from 380 in the
first half to 456 in the second"*. The percentage is right, the two figures
are invented, and they sum to 836 against a real total of 760. The actual
halves are 335 and 402. Both are now in the prompt — supplying the number
removes the gap rather than forbidding it. The narrative now reads *"335 to
402"* and *"$264.33 to $257.82"*, both real.

**2. The model borrowed an aggregate when a per-entity metric was missing.**
The second run wrote *"'Q3 Lead Gen Form | Agency Owners' average CPC rose
2.8%"* — the account-wide CPC change, reached for because that campaign's own
CPC was not among the four volume metrics listed per entity. Cost and rate
metrics are now listed per entity too. The general lesson: whatever is missing
per entity is what gets substituted from the aggregate, so the instruction
alone is not sufficient — the data has to be there.

**3. The narrative used the wrong currency.** It wrote *"₹264.33"* for a
LinkedIn file in dollars, on a deck whose KPI slide correctly rendered "$" —
the slide and the paragraph beside it disagreeing. The only currency guidance
in the prompt was the Meta Ads rule, so the model generalised it. Each source
now declares its own currency on its heading. Verified in the final run: **0
rupee symbols, 6 dollar symbols.**

Also fixed: figures are pre-formatted before reaching the prompt. Left to
insert thousands separators itself, the model wrote *"delivered 388,4961
impressions"*. Grouping digits is not a judgement call and should not be
delegated to a model concentrating on analysis.

---

## Verification summary

| Suite | Result |
|---|---|
| `verify_app_starts.py` | pass (run before every push) |
| `verify_csv_ingest.py` | 44 passed, 0 failed |
| `verify_csv_rendered_values.py` | 23 passed, 0 failed |
| `verify_csv_mapping_ai.py` | **37 passed, 0 failed** (was 2 failing) |
| `npx tsc --noEmit` | 0 errors |

---

## CLAUDE.md

Rule 13 added: never run a destructive git command (`checkout`, `reset`,
`clean`) on a file with uncommitted work — copy to a scratch path first.

---

## Still open

- **Tech-debt item 1** — `/api/comments/unread` polling frequency. Deferred.
- **Tech-debt item 2** — httpx INFO logs on stderr showing as `[error]` in
  Railway. Deferred.

Both remain logged in `docs/TECH-DEBT-NOTES.md`. Items 3, 4, 5, 6 and 7 are
now fixed.

---

## One correction to the Pass 4 report

Pass 4 stated `verify_csv_mapping_ai.py` had "2 pre-existing failures". It had
five: two from the model's judgement and three my own change had caused, by
leaving assertions that still encoded the pre-fix half-period semantics. I
checked that script's output with `tail -4`, which showed only the last two.
All five are fixed; the narrow check was the error, and it is the same
mistake in miniature as verifying a deck by recomputing its numbers — I looked
at a convenient slice of the evidence rather than the whole of it.
