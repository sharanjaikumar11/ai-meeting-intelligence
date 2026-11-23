# Action recall development follow-up

2026-11-23: the published v7 unseen baseline remains **55% recall**, 91.67% precision and 68.75% F1. Its source is commit `d9c6e1f`. Run the frozen scorer from that revision; changing model code intentionally invalidates its source-hash check.

## Changes

The v8 prompt explicitly reviews indirect next-work allocations, checks for omitted deliverables, distinguishes clarification from assigned work, and asks for contextual owner citations across split clauses. Examples are generic; no meeting IDs, reference labels or target answers are inserted into inference.

When an owner attribution still fails after the existing bounded correction, its task can now be returned with unknown owner and an explicit warning. This removes an all-or-nothing failure that previously discarded the whole meeting. No name is guessed. Invalid segment IDs, invalid schema and unsupported deadlines still fail validation. This improves availability, not a guarantee of task truth or correct ownership.

## Observed checks

| Check | Result | Interpretation |
|---|---|---|
| ES2006a live v8 extraction | Three tasks returned; all three match frozen task intent, with unknown owners and no invented deadlines | Recovered three known misses in one targeted development case |
| TS3006a replay of the two saved v7 candidates through v8 validation | Four entries retained; the invalid owner becomes unknown with a warning | Local failure recovery only; no new Gemini extraction |
| Regression suite | 178 passed | Includes retained tasks with unknown owner and rejection of invented owner citation IDs |
| Ruff / formatting / ESLint | Passed | Completed before committing |

ES2006a's third task cites the clause containing user requirements but omits the following segment containing specification; the task intent is correct, but citation coverage is incomplete. TS3006a's replay still splits summarizing and filing into separate entries and misses the industrial-design assignment. Its first-person research ownership also needs review. Four returned entries must not be counted as four correct reference tasks.

These cases are now development data. Do not combine the live retry, cached replay and unchanged v7 predictions into a claimed new unseen score or claim 85% recall. A complete v8 rerun and a new frozen meeting sample are required to assess generalization, precision and owner/detail accuracy.

## Evidence and quota

`scripts/check_recall_v8.py` reproduces the cached replay and resumes the saved live check. Outputs are under runtime `outputs/day10/recall_v8`. It uses the same persistent validation ledger, now at **20/20 attempted calls**. It does not reset the cap or retry against a different project. The temporary budgeted demo server was stopped to avoid using a stale in-memory ledger after this last request.

Next: when request budget is available, evaluate the complete v8 pipeline, review false positives and citations, and test on additional meetings whose labels are frozen before prediction. Keep this development result and the original unseen baseline separate.
