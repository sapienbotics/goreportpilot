# PHASE-1-VERIFICATION-REPORT-PASS-2

Date: 2026-08-22
Scope: closing the two external blockers from Pass 1 (OpenAI credits, migration 020) and
resolving all 7 previously-UNVERIFIED assertions with real GPT-4.1 calls.
Artifacts: `C:\mnt\user-data\outputs\csv-verification\`

---

## Headline

Both blockers are cleared. Migration 020 is live in production. All 7 previously-UNVERIFIED
assertions now resolve — 6 PASS outright, 1 initially FAILED against the real model and is now
fixed and re-verified PASS. One new defect was found and is **reported, not fixed**, per your
standing instruction to flag before touching code: the fallback narrative's Next Steps slide
renders with a title and empty body — a near-blank slide reaching a client report.

| Item | Result |
|---|---|
| Migration 020 | **Applied.** Tables, RLS, policies, indexes, trigger all verified against live schema |
| OpenAI credits | **Confirmed live** via a real completion call (`models.list()` alone had been misleadingly green the whole time) |
| 7 UNVERIFIED assertions | **6 PASS, 1 FAIL → fixed → PASS.** The failure was a real bug, found by the live model diverging from my stub's guess |
| `--cache-test` | **42/42 PASS.** Fingerprint cache confirmed working against the live DB; tripwire mechanism verified with a positive control |
| Real narrative quality | Rendered and compared side-by-side against the fallback on identical data — see below |
| New finding | Fallback narrative → blank "Next Steps" slide. **Not fixed. Flagged for your decision.** |

---

## Step 0 — Credentials

`NEXT_PUBLIC_SUPABASE_URL` in `frontend/.env.local`: `kbytzqviqzcvfdepjyby` — correct project,
confirmed before proceeding.

`SUPABASE_SERVICE_ROLE_KEY` was present but insufficient — verified against the actual
`supabase-py` `Client` object rather than assumed: its full method surface is `channel, create,
from_, functions, get_channels, postgrest, remove_all_channels, remove_channel, rpc, schema,
storage, table` — no raw-SQL or DDL method exists at any privilege level, because PostgREST has
no DDL endpoint. This matches CLAUDE.md's rule that migrations run manually via the Dashboard SQL
Editor.

The first connection string you provided (`db.kbytzqviqzcvfdepjyby.supabase.co`, direct
connection) failed DNS resolution — confirmed as a real network condition, not a typo or
credentials issue, by resolving `google.com` and the project's own API host successfully in the
same environment while only the direct-connection host failed. This is Supabase's documented
IPv6-only direct-connection behavior. Per your instruction not to retry variants, I reported the
exact error and asked for the Session Pooler string instead of guessing at alternatives.

The corrected `SUPABASE_DB_URL` in `backend/.env` was verified programmatically before
connecting: host `aws-1-us-east-2.pooler.supabase.com` (matches `*.pooler.supabase.com`),
username `postgres.kbytzqviqzcvfdepjyby` (exact match) — both asserted in code, not eyeballed.

---

## Step 1 — Migration 020: applied

Re-scanned immediately before execution (unchanged from Pass 1's hardening):

```
no DROP / TRUNCATE anywhere
statement verbs: 10 CREATE, 3 ALTER, 3 DO, 5 SELECT
```

Applied via `psycopg2` over the session-pooler connection, inside a transaction, committed only
after the verification `SELECT` returned both expected rows.

**Verified against live schema** (not just "no error thrown"):

```
csv_mappings:       id, user_id, client_id, name, column_fingerprint, mapping (jsonb),
                     is_system, created_at, updated_at
csv_mapping_usage:  id, user_id, column_fingerprint, created_at

RLS enabled:        csv_mappings=true, csv_mapping_usage=true

Policies:           csv_mappings_owner        (auth.uid() = user_id), cmd=ALL
                     csv_mapping_usage_owner   (auth.uid() = user_id), cmd=ALL

Indexes:            csv_mappings_pkey, csv_mappings_client_fingerprint_key (unique),
                     idx_csv_mappings_user, idx_csv_mappings_client, idx_csv_mappings_fingerprint,
                     csv_mapping_usage_pkey, idx_csv_mapping_usage_user_time

Constraints:         3 FKs (user_id/client_id → profiles/clients), 1 unique, 2 PKs
Trigger:             trg_csv_mappings_updated_at on csv_mappings, enabled
```

Every column, policy, index, and constraint matches the migration file exactly.

---

## Step 2 — OpenAI: confirmed live

You were right to insist on a real completion call — `models.list()` had returned success
throughout Pass 1 even while the account was fully exhausted, which is exactly why it's not a
trustworthy signal.

```python
chat.completions.create(model="gpt-4.1", messages=[...]) → "PONG"
usage: prompt_tokens=13, completion_tokens=2, total_tokens=15
```

Real completion, real token usage. Credits are live.

---

## Step 3 — Full verification chain

`verify_app_starts.py`: PASS, 103 routes, all 8 CSV routes present, no 204/response-body
conflict. `verify_csv_ingest.py`: 41/41, unchanged from Pass 1.

### Real GPT-4.1 mapping run — first pass: 34 passed, 2 FAILED

| Fixture | table_shape | date column | entity column | Notes |
|---|---|---|---|---|
| 1 LinkedIn | `wide_timeseries` ✓ | `Start Date (in UTC)`, `%Y-%m-%d`, conf 1.00 ✓ | `Campaign Name`, conf 1.00 | All 6 columns mapped, all PASS |
| 2 German | `wide_timeseries` ✓ | `Tag`, `%d.%m.%Y`, conf 1.00 ✓ | `Kampagne`, conf 1.00 | Totals row still correctly excluded; all PASS |
| 3 Meta xlsx | `wide_timeseries` ✓ | `Reporting starts`, conf 1.00 ✓ | `Campaign name`, conf 1.00 | **CTR mapped as `unit: "ratio"`, not `"percent"` — 2 assertions FAILED** |
| 4 Semrush | `wide_entity` ✓ | `Date`, conf 1.00 | `Keyword`, conf 1.00 | `Cost` ambiguity raised as expected ✓ |
| 5 Legacy | `long_kpi` ✓ | none (correct — no date column exists) | — | Byte-identical to `parse_kpi_csv` ✓ |

### The failure — a real bug, found by the model diverging from my stub

Fixture 3's CTR column ("CTR (all)", stored as `0.0047`) was mapped by the live model as
`unit: "ratio"`. My Pass-1 stub had guessed `"percent"`. Both are defensible readings — arguably
`"ratio"` is the *more* precise one for a column with no `%` sign anywhere in it — but my scaling
code, `_percent_scale()`, only triggered on the literal string `"percent"`:

```python
if mapping.unit != "percent":
    return 1.0
```

Two lines away in the same file, `_slide_unit()` already collapses `"percent"` and `"ratio"` to
the same rendered `%` display. The scaling function's condition was narrower than the display
function's, so a ratio-labelled fraction rendered as `%` without ever being multiplied by 100:
**`0.0047%` instead of `0.47%`** — reproducing the exact defect I'd fixed in Pass 1, just reached
through a mapping-unit choice my stub hadn't anticipated.

**Fixed:** widened `_percent_scale`'s trigger to `mapping.unit in ("percent", "ratio")`, matching
`_slide_unit`'s existing grouping. Re-ran against the exact fixture that exposed it:

```
CTR (all) -> ctr  ratio  higher_is_better  conf=0.95
  ...
  CTR (All)   current=0.4975   previous=0.4767   unit=percent   change=4.37
  warnings: ['CTR (All) was stored as a decimal fraction (0.0047) and has been
             converted to a percentage (0.47%).']
  PASS  CTR renders as a percentage (~0.49%), not the raw 0.0047
  PASS  fraction scaling is disclosed, not silent
```

Full suite re-run end to end after the fix: **36/36 passed, 0 failed.**

### Divergences from the stub, in full

The task asked specifically to call these out — they're the real signal a hand-written stub
can't provide:

- **Fixture 3, CTR unit:** stub guessed `"percent"`, model chose `"ratio"` — the divergence that
  exposed the bug above.
- **Fixture 3, "Results" column:** stub didn't model this as ambiguous. The live model raised a
  genuine ambiguity — *"What specific outcome does the 'Results' column represent in this export
  (e.g., conversions, leads, video views, or another objective)?"* — at confidence 0.60/0.70
  across two runs, correctly below the 0.80 threshold. This is exactly right: "Results" is
  Meta's user-configurable objective field and genuinely cannot be inferred from column name and
  samples alone. My stub had confidently mapped it to `"results"` at 0.90 — the model's
  skepticism here is better calibrated than my guess was.
- **Fixture 4, "Cost":** stub predicted an ambiguity between "estimated traffic value" and "ad
  spend"; the live model raised the same ambiguity both times it ran, phrased as "advertising
  spend vs. cost of goods/services" — same concern, different framing. Confirms the ambiguity
  path fires reliably on genuinely ambiguous columns, not just on my specific phrasing guess.
- **Everything else** (table_shape, date columns/formats, entity columns, the sum-vs-average
  behavior, the German totals-row exclusion, the legacy long-KPI parity) matched the stub's
  predictions closely, with minor confidence-score jitter between runs (e.g. 1.00 vs 0.95 on
  "Link clicks") consistent with `temperature=0.1`, not a concern.

### `--cache-test`: 42/42, tripwire confirmed with a positive control

```
using client 'videogenie' (c784fbe9-4b1f-4d09-8ee9-f15a6d88c4f1)
PASS  mapping persisted to csv_mappings
PASS  saved mapping found by column fingerprint
PASS  stored mapping rehydrates
PASS  replayed mapping is marked as reused, not AI
PASS  replayed mapping still normalizes correctly
PASS  NO OpenAI call on the repeat upload
cleaned up the test mapping row
```

One nuance worth being precise about, since I don't want to overstate what "confirm the tripwire
would have raised" means: the tripwire's `AssertionError` **does** fire when the OpenAI client is
actually called — confirmed with a positive-control test that intentionally routed a mapping call
through the tripwire and observed the exception in the traceback. But that exception never
propagates to a caller, because `propose_mapping()` deliberately catches all exceptions for
graceful production degradation (documented behavior: "never raises on a model failure"). So the
cache-test correctly uses a **call counter**, not exception-catching, to detect whether the client
was invoked — that design was right, and the positive control confirms the counter would have
incremented had the real cache-hit path fallen through to a network call. It didn't.

---

## Step 4 — Real narrative quality vs. fallback

Generated both on **identical data** — the real LinkedIn fixture, mapped by the live model,
normalized, and rendered through the actual (now chart-overlap-fixed) `modern_clean` template.
The fallback used the real `_fallback_narrative()` function against the same data, not
hand-typed placeholder text.

**Executive Summary** — real vs. fallback:

> *Real:* "Acme Ltd entered July with steady ad momentum but limited website data, so this
> update centers on LinkedIn Ads. Over the first 10 days, total conversions jumped 23.3%,
> powered mainly by the 'Lead Gen - Enterprise' campaign... cost per conversion improved by
> 12.2%... we will shift more budget to high-performing LinkedIn campaigns..."

> *Fallback:* "Performance summary for Acme Ltd, 2026-07-01 to 2026-07-10. The figures in this
> report are complete and accurate. Written commentary is being finalised and will be added
> shortly."

**Key Wins** (real) — three specific, numbered claims citing named campaigns and exact figures:
*"Lead Gen - Enterprise drove conversions up from 30 to 37 (+23.3%) on LinkedIn Ads." / "Cost
per conversion on LinkedIn Ads dropped 12.2%, from $49.16 to $43.15." / "Retargeting - Website
Visitors contributed to a 10.6% increase in LinkedIn clicks (804 from 727)."*

**Concerns** (real) — same pattern, one recommendation per named campaign: Q3 Brand Awareness's
slower conversion growth, Retargeting's lagging conversion rate, Lead Gen's rising spend share.

**Next Steps** (real) — three numbered, quantified action items: reallocate 15% of spend from
Q3 Brand Awareness to Lead Gen - Enterprise, test new creative for Retargeting, monitor Lead
Gen's cost per conversion.

Screenshots of all rendered slides (both decks) are in the outputs folder:
`slide_real_gpt41_{exec_summary,key_wins,concerns,next_steps}.png` and
`slide_fallback_{exec_summary,next_steps_BLANK}.png`.

The narrative correctly cites campaign names (`Q3 Brand Awareness`, `Retargeting - Website
Visitors`, `Lead Gen - Enterprise`) despite no chart on the deck ever visualizing them — this
matches exactly what I reported to your earlier question: the entity breakdown reaches the model
as a "Top entries" name list in the prompt, so the narrative can name campaigns even though the
chart cannot. One limitation visible in this output: the model can *name* a lagging campaign
("Retargeting - Website Visitors lagged in conversions") but couldn't cite a specific number for
it in the Concerns slide's first draft (a re-run instance said "(data not specified)") — because
only aggregate totals and entity *names* are passed into the narrative prompt, not per-entity
metric values. Worth knowing if per-campaign narrative precision becomes a priority later; not
something I'm proposing to change now.

---

## New finding: fallback narrative → blank "Next Steps" slide

**Not fixed. Reporting only, per your standing instruction to flag before touching code.**

Comparing the fallback deck slide-by-slide (exactly what Step 4 asked for) surfaced this: the
fallback deck has 5 slides where the real deck has 7. `slide_selector.py`'s post-selection
cleanup removes the `key_wins` and `concerns` slides when their narrative content is empty —
correct, confirmed working, no blank slides for those two. But the removal list is:

```python
# slide_selector.py:150
for key in ("key_wins", "concerns"):
```

`next_steps` is missing from that tuple, despite being structurally identical in every other
respect — same `lambda d: True` predicate, same list-or-string content handling, adjacent slide
index (17, next to 15 and 16). Rendered and confirmed visually
(`slide_fallback_next_steps_BLANK.png`): the fallback deck's final slide shows the title "Next
Steps & Action Items," the theme's purple footer band, and **nothing else** — an empty body
reaching a client.

**This gap was dormant until my Pass-1 fix made it reachable.** Before Pass 1, the fallback's
`next_steps` value was `"1. Regenerate this report to get AI insights"` — non-empty, so the
missing-from-tuple gap never fired. My Pass-1 change (making the fallback text neutral and
internals-free, per the leaked-billing-URL fix) set `next_steps: ""`, which exposed this
pre-existing inconsistency for the first time. I'm treating this as my responsibility to flag
clearly rather than quietly patch.

**Scope, if you want it fixed:** one line — add `"next_steps"` to the tuple at
`slide_selector.py:150`. Blast radius: any report where the narrative engine fails for *any*
reason (not CSV-specific), which is every report generation path, not just this feature. Low
risk, small diff, but it's a behavior change to core report assembly outside Track A's
boundaries, so I'm asking rather than assuming.

---

## Verification commands (current state)

```bash
cd backend
python scripts/verify_app_starts.py             # PASS, 103 routes
python scripts/verify_csv_ingest.py              # 41 passed, 0 failed
python scripts/verify_csv_mapping_ai.py          # 36 passed, 0 failed (real GPT-4.1)
python scripts/verify_csv_mapping_ai.py --cache-test   # 42 passed, 0 failed
```

## What needs a decision

1. **Fix the blank Next Steps slide?** One line, `slide_selector.py:150`. Flagged, not applied.
2. Browser pass (a)–(f) — ready whenever you sign in. Both real blockers are now clear, so (b)'s
   ambiguity guardrail can actually be tested against a live model this time.

## Commits this pass

```
24809f0  fix(csv): fraction-rate scaling missed columns the model labels "ratio"
```

(Migration 020 was applied directly to the database — not a git commit, no code changed for it.)

## Commits carried from Pass 1

```
282c0fa  fix(pptx): chart image overlapped the last KPI row on 2 of 6 templates
2bc982f  docs: Phase 1 verification report
057b3e3  fix(csv): repair production outage — 204 route + postponed annotations
7124c36  fix(csv,narrative): three defects found by Phase 1 verification fixtures
d166c56  feat(csv): universal CSV/XLSX ingestion with AI column mapping
fb43e86  refactor(sources): add adapter seam, collapse duplicated pull blocks, fix regenerate
```
