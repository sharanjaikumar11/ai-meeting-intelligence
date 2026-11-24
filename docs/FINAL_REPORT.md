# AI Meeting Intelligence Agent final report

**Date:** 24 November 2026

**Repository:** https://github.com/sharanjaikumar11/ai-meeting-intelligence

**Release candidate:** action extraction v9; Whisper small; Gemini 2.5 Flash; local pyannote speaker diarization.

The required application, structured JSON output, interactive interface, evaluation report and documented GitHub repository are implemented. The real recording demonstration now includes live reviewed question answering. Accuracy improved on the development regression, but the requested 85–90% recall target has not been established across unseen meetings. This is a working evaluated project, not a claim of error-free meeting understanding.

## Requirements checked against the supplied task document

| Requirement | Implementation and verification |
|---|---|
| Accept audio/video; Whisper transcription; timestamps | Local media decoding and timestamped Whisper pipeline; real AMI audio and MP4 format checks; WER measured against human transcripts |
| Speaker identification | Anonymous diarization labels aligned to transcript segments; confirmed names require evidence or user mapping; speaker errors remain possible |
| Summary and key discussion points | Gemini structured summaries with exact transcript citations and a review pass |
| Actions, assigned persons, deadlines, pending questions | Structured extraction, separate owner/deadline validation, explicit unknowns and unresolved event-relative dates |
| Changing decisions and deadlines | Ordered decision histories, replacement/reopening/recall events, disagreements and unresolved discussions; real chip-replacement and Friday/Monday deadline examples documented in the Days 1–5 review |
| Final agreed decision | Agreed, tentative and unresolved states distinguished within the supplied recording interval |
| Interactive assistant | FastAPI, HTML/Tailwind/JavaScript UI, meeting questions, evidence expansion and JSON download |
| WER; action/decision precision, recall and F1; QA correctness | All required metric categories measured and reported below, with sample size and evaluation scope |
| Python app, JSON, QA UI, evaluation report, GitHub/README/setup | Available locally and in the public repository; setup, dependency pins and pre-commit checks included |

All ten implementation days are checked in `docs/PLAN.md`. Completing the implementation plan does not mean the remaining model-accuracy limitations are solved.

## Accuracy results

### Same 20-task comparison

The v7 baseline was frozen before prediction on six project-unseen excerpts. These cases became development data when their errors were inspected and used to improve v8/v9. The v9 row is therefore a **development regression**, not a new unseen score.

| Metric | Frozen v7 baseline | Revised v9 on the same cases |
|---|---:|---:|
| Correct tasks / reference tasks | 11/20 | 15/20 |
| Precision | 91.67% | 88.24% |
| Recall | 55.00% | **75.00%** |
| F1 | 68.75% | **81.08%** |
| False positives | 1 | 2 |
| False negatives | 9 | 5 |
| Correct owners among matched tasks | 8/11 | **13/15** |
| Complete/correct details among matched tasks | 8/11 | **13/15** |
| WER on unchanged transcripts | 21.44% | 21.44% |

Recall rose by 20 percentage points and F1 by 12.33 points; precision decreased by 3.43 points. One v7 extraction failure is included as four missed tasks, not excluded from the denominator. All six v9 extractions returned results. Remaining misses include technical-functions design work and research/interview/working-design tasks. An underspecified “get that information” output was not generously matched to a specific reference task.

### Fresh meeting and subsequent retest

ES2009a was not previously used for development. Its labels were frozen before ASR/extraction. The scope is two excerpts totaling 165 seconds and four reference tasks, **not the full meeting**.

| Metric | Fresh v8 result, before tuning | v9 development retest |
|---|---:|---:|
| Precision | 80% (4/5) | 100% (4/4) |
| Recall | 100% (4/4) | 100% (4/4) |
| F1 | 88.89% | 100% |
| Correct owners | 2/4 | 3/4 |
| Complete/correct task details | 2/4 | 3/4 |
| WER | 16.46% (81/492 words) | Unchanged |

The original fresh result had an extra audience caution presented as work. The retest removes it and restores the explicit first-person document owner. One UID attribution remains ambiguous under the frozen conservative owner rubric, and the document task omits trade-off detail. The next-meeting deadline is retained without inventing a calendar date. Four tasks are too few to support a broad recall claim; the v9 retest must not be described as a second unseen test.

### Other required metric categories

The frozen Day 9 pilot remains the measured reference for decisions and QA; these aggregates were not rerun or silently replaced by later targeted successes.

| Metric | Frozen Day 9 result |
|---|---:|
| WER | 28.27% (480/1,698 words) |
| Action precision / recall / F1 | 50.00% / 40.00% / 44.44% |
| Final-decision precision / recall / F1 | 100.00% / 33.33% / 50.00% (1 TP, 0 FP, 2 FN) |
| Strict QA correctness | 4/6 = 66.67% |

One correct decision prediction does not establish reliable 100% precision. Later live QA checks correctly separated the two designers' work, described the voice-recognition decision without the earlier incorrect budget claim, and answered the demonstration question; they are individual checks, not a new aggregate QA benchmark.

## Accuracy changes made

- Recognize indirect next-work allocations and review the transcript for omitted deliverables.
- Retain tasks with unknown owners if owner attribution still fails after one correction, while keeping invalid citation IDs, schema and deadlines rejected.
- Accept supported first-person phrases `I'm`, `I’m` and `I am` for commitments without guessing a person's name.
- Distinguish general cautions from concrete tasks, preserving actions such as reviewing an invoice or preparing a quote.
- Preserve task scope and contextual citations, and discourage assigning a nearby role without a clear task-owner link.

The last item remains imperfect: prompt guidance and exact-quote checks cannot guarantee semantic ownership. Beam-size-5 evaluation uses the same frozen transcripts across versions; no WER improvement is attributed to action-prompt changes.

## Completed demonstration and release checks

A real 60-second AMI MP4 completed transcription/speaker labeling, summary, actions and decision tracking. Downloaded JSON exactly matched saved results. The remaining live QA was completed on 24 November: it correctly identified the remote-control design purpose and the original/trendy/user-friendly brief, with verified citations. Meeting ID: `d6992b7818a74fe7b64002f52cf7d0a2`. The upload stages were saved on 23 November and resumed for QA; this was not a second complete retranscription. The historical action output in this demonstration predates v9; v9 actions were separately exercised live on eight excerpts and covered by integration tests.

**Final checks: Ruff lint passed; Ruff formatting passed; ESLint passed; 185 tests passed.** One earlier run timed out in an asynchronous retry test; that test passed in isolation and the subsequent full suite passed. Tests use mocked model responses unless explicitly described as live above. Desktop/mobile UI checks passed with explicitly mocked section/QA fixtures; the real completed meeting was also inspected in the UI. The dependency smoke test verified imports, FFmpeg, TorchCodec, a local API request and metric calculations. A clean installation on a second machine was not performed.

The active Pacific-day validation ledger contains 15 attempts: 13 successful responses and two service/transport failures. The previous exhausted 20-attempt ledger was preserved. No quota bypass or model substitution was used.

## Deliverables and reproduction

| Deliverable | Location |
|---|---|
| Application and UI | `meeting_intelligence/` |
| Setup and launch | `README.md`, `docs/SETUP.md` |
| Required evaluation | `evaluation/day09_metrics.json`, `docs/DAY_09.md` |
| Original 20-task baseline | `evaluation/day10_unseen_metrics.json` |
| Fresh-meeting references, review and metrics | `evaluation/fresh_v8_*.json`, `docs/FRESH_MEETING_V8.md` |
| Revised development comparison | `evaluation/release_v9_*.json`, `scripts/score_release_v9.py` |
| Real combined JSON and QA evidence | Runtime `outputs/day10/final_2026-11-23/demo.result.json` and `demo.json` |
| Repeatable checks | `scripts/check.ps1` (Ruff, format check, ESLint, pytest) |

Run from the repository in PowerShell:

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$runtime\.venv\Scripts\python.exe" -m meeting_intelligence.web --environment-root $runtime --port 8001
```

Open http://127.0.0.1:8001. Audio/model files, credentials, virtual environments and runtime outputs remain outside Git. The final v9 scoring command is:

```powershell
& "$runtime\.venv\Scripts\python.exe" scripts/score_release_v9.py --environment-root $runtime
```

Source and artifact hashes bind the reviews. The fresh v8 source/results were archived before v9 edits in runtime `outputs/day10/fresh_v8_ES2009a/fresh_v8_bundle.zip`. Historical scorers require their matching frozen source revision or archived source; they should reject modified candidates.

## Limits and remaining research work

The assignment deliverables are complete within the documented scope. The 85–90% broad recall aspiration remains unproven. All structured reference labels and semantic reviews are assistant-authored from AMI human transcripts, without independent annotation review. Samples are small, selected and dominated by design meetings; speakers were not split into a formal independent benchmark. Speaker identities, task details and decisions can still be wrong. The teletext decision remains ambiguous in the source and requires independent listening; it is not declared fixed.

The application is a local single-user service. It has no production authentication or multi-user deployment, and transcript text is sent to Gemini. Task status means what was said in the supplied recording, not current real-world completion. No positive deadline-change accuracy benchmark or diarization error-rate benchmark is claimed. These limitations should accompany any demonstration or submission.
