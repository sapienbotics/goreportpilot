# PHASE-1-VERIFICATION-REPORT-PASS-3

Date: 2026-08-22
Scope: Step 5 browser pass (a)–(f) against production, now that both external blockers from
Pass 1/2 (OpenAI credits, migration 020) are resolved.
Account: Sapienbotics (`saurabh.valetudeprimus@gmail.com`), client `videogenie`
(`c784fbe9-4b1f-4d09-8ee9-f15a6d88c4f1`) — the same client used in Pass 2's `--cache-test`.

---

## Headline

5 of 6 sub-tests fully verified against live production, driven through the real UI with real
file uploads and the real (credited) model. One — (e), full report generation — is genuinely
blocked by the account's trial-expired billing state, not by anything in the code; I did not
attempt to work around it. Two new findings surfaced during testing, both reported, neither
fixed without your say:

| Test | Result |
|---|---|
| (a) LinkedIn — confidence indicators, normalized preview | **PASS** |
| (b) Semrush — ambiguity renders, Confirm genuinely blocked | **PASS** — proven by an actual click that did nothing |
| (c) German — locale preview `1.284,50 → 1284.5` etc. | **PASS** |
| (d) Save mapping, re-upload, one-click reuse | **PASS**, with a real gap found: the ambiguity resurfaces every time |
| (e) Generate full report, download PPTX | **BLOCKED** — trial expired, no code path to test through the UI |
| (f) No-numeric-columns file — actionable failure message | **PASS** |
| — | **New finding:** "2 columns need your confirmation" over-counts a single column with two reasons |
| — | **New finding:** saved mappings never clear their ambiguities, so a resolved question reappears on every future upload |

---

## A note on tooling, before the results

Testing (a)/(b)/(c)/(d)/(f) required uploading real files, and the in-app Browser pane (where
you signed in) **cannot do this** — confirmed precisely, not assumed: `HTMLInputElement.value`
for `type="file"` can only be set programmatically to the empty string in any browser, by web
platform security design, and the sandboxed pane can't render or drive a native OS file picker
either (confirmed — clicking the drop zone produced no dialog). No workaround exists from that
surface.

I found your Chrome ("Claude in Chrome") was already signed into the same account — same
session, no separate sign-in needed — and it has a dedicated `file_upload` tool built exactly
for this. All browser testing below ran there instead.

---

## (a) LinkedIn — confidence indicators, normalized preview: PASS

Uploaded `linkedin_ads_export.csv`. Real model, real production:

- "Mapped automatically — check it below" · 10 rows · 8 columns
- All 6 metrics at **High** confidence, each with its reasoning shown as a subtitle
  ("Standard ad metric, unambiguous header", etc.)
- "6 metrics ready." — Confirm enabled immediately, no ambiguities
- Expanded "Check how the first rows are read": `0.91% → 0.91`, `248.00 → 248`, `4 → 4`,
  `62.00 → 62` — every value parsed correctly, shown before commit

## (b) Semrush — the priority test: PASS, proven behaviorally

Uploaded `messy_semrush_export.csv`. The ambiguity rendered inline exactly as designed:

> *"Does 'Cost' represent actual ad spend, or is it SEMrush's estimated traffic value for the
> keyword?"* — `ad_spend` / `estimated_traffic_value` / `Leave it out`

**I didn't just observe the Confirm button's styling — I clicked it.** With the ambiguity
still open, clicking "Use this data" did nothing: same dialog, same state, no error, no close.
That's the actual guardrail working, not an assumption about disabled-button CSS.

Clicking `ad_spend` resolved it live: the Cost row's badge changed from amber "⚠ Check this" to
green "✓ Confirmed", the footer changed from *"2 columns need your confirmation before this can
be used"* to *"5 metrics ready,"* and Confirm became genuinely clickable (confirmed by then
using it to commit).

**New finding — the "2 columns" count is wrong.** Only one row (`Cost`) ever showed a blocking
state in the table; `Traffic %` showed "Medium," which by design isn't meant to block. Checked
the code:

```js
// CSVMappingDialog.tsx:78
for (const column of mapping.columns) {
  if (column.confidence < threshold && !resolved.has(column.source_column)) {
    out.push(column.source_column)     // "Cost" pushed here...
  }
}
for (const ambiguity of mapping.ambiguities) {
  if (!answered.has(ambiguity.column)) out.push(ambiguity.column)   // ...and again here
}
```

Both loops reference the same column name, so `blockers` = `["Cost", "Cost"]`, length 2, for
what is really one column with two overlapping reasons to need attention. **The guardrail
itself is unaffected** — `canConfirm` still correctly requires `blockers.length === 0` — this
is purely a miscount in the human-readable message. Not fixed; flagging per your instruction.

## (c) German — locale preview: PASS

Uploaded `google_ads_de_export.csv`. Totals-row banner rendered ("Row 7 looks like a totals row
and was excluded so it isn't double-counted"), date format detected as `%d.%m.%Y`, German
column names recognized with reasoning ("German for impressions; values are large integers
typical for ad impressions"). Preview showed every value correctly: `1.284,50 → 1284.5`,
`1.998,75 → 1998.75`, `12.450 → 12450`, `3,12% → 3.12`. The specific `8.276,85` figure you named
is the totals row itself (an aggregate, excluded from any raw-row preview by design); the
individual rows shown sum to exactly 8276.85, consistent with the backend-level proof in Pass 2.

## (d) Save, re-upload, one-click reuse: PASS, with a real gap found

Saved the Semrush mapping as "Monthly Semrush export," confirmed it, then re-uploaded the same
file. The UI correctly showed **"✓ Reused your saved mapping 'Monthly Semrush export'"** —
proof the fingerprint-cache mechanism works end to end through the real UI, not just in Pass 2's
backend script.

**New finding — the saved mapping doesn't persist ambiguity resolution.** The Cost ambiguity
reappeared on the replayed upload, asking the identical question again, and the footer again
said a column needed confirmation. Checked the code:

```js
// CSVMappingDialog.tsx:183 — confirm()
const finalMapping: ColumnMappingProposal = {
  ...mapping,                          // ambiguities array carried through unchanged
  columns: mapping.columns.map((c) =>
    resolved.has(c.source_column) ? { ...c, confidence: 1 } : c,
  ),
}
```

`confirm()` bumps confidence to 1.0 for touched columns but spreads the *original* `mapping`
first — `ambiguities` is never cleared before the object is sent to `commit()` and saved
verbatim. Every future upload of this file layout will ask the same question forever, which
undercuts the "next month is one click" promise for any source that ever had an ambiguity.
Root cause confirmed in code, not fixed — flagging per your instruction.

## (e) Generate full report, download PPTX: BLOCKED — not a code fault

Confirmed precisely rather than assumed: with the trial expired, the "Generate Report" submit
button is not merely disabled — **it doesn't render at all.** Scrolled the full Reports tab;
the CTA area is entirely replaced by the "Trial expired — upgrade to generate reports" banner.
There is no code path to test through this account's current UI state.

I did not attempt to bypass or alter billing/subscription state to force this through — that's
outside what I should do without being asked. The underlying feature is independently proven:
Pass 1 and Pass 2 both generated full reports end-to-end via direct backend calls (real mapped
CSV data → real charts → real PPTX, verified visually), so report generation itself works. What
remains unverified is specifically *the browser click path* on an active-plan account.

## (f) No-numeric-columns file: PASS

Built a 4-column, all-text fixture (`Campaign Name, Status, Owner, Notes`) and uploaded it.
Production response: **"We found columns but none of them looked like a metric we can chart.
Pick the ones you want below."** — specific, names what was found, says what to do next. Not a
generic error. "0 metrics ready," Confirm correctly disabled.

Checked whether the "add a column manually" chips appear for a file with zero numeric columns:
they correctly don't, because `unmappedColumns` only offers columns the profiler typed as
`'number'` — since none of this file's columns are numeric, there's genuinely nothing to
manually promote into a metric, and the UI reflects that rather than offering a broken option.

---

## What needs a decision

1. **Fix the "2 columns" double-count?** One-line dedup in `CSVMappingDialog.tsx`'s `blockers`
   computation. Cosmetic only — the guardrail itself is correct.
2. **Fix ambiguities not clearing on save?** This one has real product impact — it's the
   specific thing that breaks the "one click next month" promise for any ambiguous source.
   Scope: clear `ambiguities` (or mark them resolved) on the columns/proposal that gets sent to
   `commit()` with `save_as` set. Not yet sized in detail; flagging for your call before I look
   closer.
3. **(e) remains unverified through the browser.** Upgrade the account's plan, or tell me
   another way you'd like this exercised, and I'll complete it.

## Cleanup

The "Monthly Semrush export" mapping saved during (d)/(b) testing is real, legitimate saved
data in your production account — I left it in place rather than deleting it unprompted. Say
the word if you'd like it removed.

## Commits this pass

None — every issue found this pass is reported, not fixed, per your standing instruction to
flag scope before touching code.
