# Day 8 — completed 2026-11-20

The planned varied-recording, edge-case and hallucination checks are complete. This is functional and qualitative validation, not a claim of perfect transcription/extraction or a substitute for Day 9 metrics.

## Scope and results

Three additional full recordings were downloaded from the [official AMI distribution](https://groups.inf.ed.ac.uk/ami/download/). Attribution: AMI Consortium / University of Edinburgh, CC BY 4.0. URLs, SHA-256 hashes and full durations are in runtime `data/day08/provenance.json`. These are development/error-analysis cases, not an untouched evaluation set.

| Meeting | Download duration | Tested interval | Segments | Predicted / reference speakers | Final reviewed result |
| --- | ---: | --- | ---: | --- | --- |
| ES2005a | 477.88 s | Whole recording | 87 | 4 / 4 | Research tasks retained; unknown owners/deadlines kept unknown; no invented final design consensus |
| IS1001b | 2116.69 s | 1700–2090 s | 133 | 3 / 4 | Follow-up summary/sharing/email work retained; wheel agreement preserved; QA correctly excludes LCD and speech control |
| TS3005d | 2672.20 s | 1500–1810 s | 177 | 4 / 4 | Curve retained; speech recognition and scroll wheel dropped; product specifications omitted from tasks |

Full files were downloaded, but only the listed intervals of the longer meetings were processed. Speaker counts are diagnostics, not diarization accuracy. ES2005a human word annotations end near 306 seconds; transcript content after that point was not validated against those annotations.

All three recordings now have structured results in the local application. **279 extraction evidence references and 20 retained QA evidence references** were checked against exact transcript quotes, timestamps and speaker IDs, with source fingerprints validated. Correctness was also reviewed against relevant human-reference turns; citation validity alone was not treated as semantic correctness.

Supported and unanswerable questions were checked for all three meetings. ES2005a's previously verified bank-account abstention was reused; its owner question was rerun and now gives a partial answer after unsupported owner claims are omitted. IS1001b and TS3005d correctly declined the unsupported bank-account question.

TS3005d used **one bundled real Gemini call for actions, decisions and two answers**, followed by local validators and manual comparison with AMI reference turns around 1774–1799 seconds. It did not receive a separate model-review call. ES2005a and IS1001b QA used draft-and-review calls. The earlier authored deadline/prompt-injection fixture was already verified and was not rerun unnecessarily.

## Quota use

The 2026-11-20 completion run used **exactly 20 attempted Gemini calls**, with 19 usable API responses and one request failure without a usable response. Invalid schema/evidence drafts also consumed calls and were retained for diagnosis.

The runner:

- Counts every SDK attempt before sending it, including failures.
- Uses no automatic SDK retries.
- Spaces call starts by at least 16 seconds, below the observed 5 RPM allowance.
- Stops at a persistent local cap of 20 attempts.
- Reuses saved transcripts, validated summaries and cached responses.
- Batches independent questions to reduce calls without merging their answers.

This ledger measures this runner's attempts; it cannot measure other clients using the same Google project. It is not evidence of the project's exact remaining server quota.

## Edge cases and fixes

| Check | Observed issue | Verified handling |
| --- | --- | --- |
| 20-second digital silence | Whisper invented “you” | Exact-zero PCM guard bypasses models; empty transcript, summary, actions and decisions verified directly and through upload |
| Corrupt recording | Unusable input | Actionable decode error; no invented result |
| Video with no audio | Missing audio stream | Specific error |
| Offset after recording end | Invalid interval | Specific error |
| Blank question | Previously reached server-error handling | HTTP 422 validation |
| Anonymous owners | “me” treated as a name; recipients inferred from nearby turns | Pronoun/name rejection; unsupported anonymous ownership claims omitted with a partial-answer limitation |
| Monetary decision | Recalled price unsupported by its cited numbers | Entire unsupported monetary topic omitted; no replacement amount guessed |
| Rejected alternative | Withdrawing a ball proposal erased the agreed wheel | Existing agreement preserved when withdrawal explicitly targets only unresolved alternative proposals |
| Product choices | Colors/components extracted as tasks | Concrete-work prompt plus conservative product-choice guard; omitted items documented in warnings |
| Invalid model JSON/evidence | Schema/citation failures | One bounded correction for actions/summary; exact IDs still validated; failed drafts preserved |
| Restart/failure recovery | Partial stages needed reuse | Saved stages retained; existing API recovery tests pass |

The authored robustness fixture separately verified Friday remains agreed after rejecting Monday, hosting remains unresolved, accessibility ownership remains unknown, and a quoted malicious instruction does not establish a launch approval. This is authored text, not a recorded AMI meeting.

## Noisy-audio test

A clean 70-second ES2005a section (170–240 s) and a deterministic copy with added 5 dB SNR noise were transcribed with the real local models. Each produced 17 segments and two estimated speakers; both retain short-clip speaker limitations.

The noisy transcript contained substantial word corruption: 44 of 122 scored words had Whisper probability below 0.35, compared with 10 of 123 in the clean copy. These probabilities are **not calibrated accuracy scores**.

A warning is added when at least 20% of ten or more scored words are below 0.35. At 30%, the conservative analysis gate requires audio/transcript review before any transcript is sent to Gemini. The saved noisy sample triggered that gate; the downstream test confirmed **zero Gemini calls**. This is an intentionally blocked unreliable-input case, not a successful extraction-quality result. Quiet speech is not removed by the digital-silence guard: even one nonzero sample prevents that shortcut.

## Final validation and artifacts

**148 automated tests passed** in the final suite, including quota caching/caps, bounded corrections, source evidence, owner guards, numeric guards, proposal withdrawal, quality gates, and existing application regressions.

Runtime artifacts:

- `outputs/day08/completion_2026-11-20/request_ledger.json`: all 20 attempts.
- `outputs/day08/completion_2026-11-20/final_review.json`: validation counts and semantic-review findings.
- `outputs/day08/completion_2026-11-20/*.result.json`: revised structured results.
- `outputs/day08/completion_2026-11-20/*.qa.json`: validated answers and review-method notes.
- `outputs/day08/edge_reports.json` and `local_checks.json`: earlier real audio/API checks.
- Pre-guard results and raw model responses are preserved alongside corrected outputs.
- Original web results/state are backed up as `*.before_day08_completion` in each job directory.

Updated guards were applied deterministically to saved real-model outputs, not passed off as newly generated answers. Results were republished only after validation and reference-based review assertions passed. No reference transcript was substituted for Whisper output.

## Reproduce safely

From the source repository:

```powershell
$root = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$root\.venv\Scripts\python.exe"
$env:MEETING_ENV_ROOT = $root
& $python -m pytest tests -q
# Revalidate and publish already-recorded outputs locally; no Gemini calls:
& $python scripts\finalize_day08_local.py --environment-root $root --publish
```

`prepare_day08.py` downloads the sources. `complete_day08_budgeted.py` is the resumable capped runner. `finish_day08_last_call.py` performed the final bundled request using the same ledger. Do not create a fresh run label to evade the exhausted per-run budget; a new live evaluation needs available project quota and an explicit new budget.

Earlier failures and quota interruptions are retained in [the historical Day 8 log](DAY_08_HISTORY.md).

## Remaining accuracy limitations / Day 9 boundary

IS1001b still under-separates four reference speakers into three. Matching the total speaker count elsewhere does not establish correct word-level assignments. Overlapping speech and ASR mistakes remain. Conservative guards can omit genuine implicit tasks, ownership or numeric paraphrases; their thresholds/rules are not calibrated guarantees. Product-choice filtering is intentionally limited to observed hardware-discussion patterns.

Negative feature choices in IS1001b are represented as withdrawn topics; the supporting events and QA establish exclusion, rather than claiming positive inclusion. ES2005a owner QA remains partial because speaker identity cannot be established reliably from acknowledgements.

The completed Day 8 scope is testing and handling these failure modes with traceable, conservative output. Formal WER, action/decision precision-recall-F1 and QA correctness on a separately reviewed evaluation set remain **Day 9**.
