# Day 9 evaluation artifacts

Completed 2026-11-22: this folder contains the frozen structured reference, hash-bound semantic review ledger, scoring tools and compact metrics report. See [historical DAY_09_PROTOCOL](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs/DAY_09_PROTOCOL.md) for inclusion, matching and scoring rules, and [historical DAY_09](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs/DAY_09.md) for results and limits. `day09_review_progress.json` is historical evidence from the quota pause; `day09_adjudication.json` supersedes it.

The reference is **assistant-authored from AMI human transcripts**, not independently human-validated gold. It was fixed before inference. Scores describe a small purposive pilot only. Do not use these three excerpts for further tuning and still call them held-out test data.

## Reproduce

The working application now includes Day 10 changes. To reproduce the original Day 9 scores, extract `outputs/day09/day09_evaluation_bundle.zip`, use its `source` directory, and place the bundled `outputs/day09` beneath the environment root. The original scorer intentionally rejects the changed working checkout. See [historical DAY_10_IMPROVEMENTS](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs/DAY_10_IMPROVEMENTS.md) for the separate known-example improvement check.

Run from the source repository in PowerShell:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$envRoot\.venv\Scripts\python.exe"
& $python scripts/evaluate_day09.py --environment-root $envRoot --stage prepare
& $python scripts/evaluate_day09.py --environment-root $envRoot --stage transcribe
& $python scripts/evaluate_day09.py --environment-root $envRoot --stage extract
& $python scripts/score_day09.py --environment-root $envRoot
```

While Gemini is paused, `scripts/score_day09.py --environment-root $envRoot --local-only` produces `local_metrics.json` after all three transcriptions finish. It deliberately leaves action/decision/QA aggregate scores null. The complete scorer requires all predictions and the reviewed `day09_adjudication.json`; it cannot mistake an incomplete run for a completed evaluation.

Existing predictions and raw Gemini responses are reused; scoring itself makes **zero API calls**. The extraction runner has a persistent 20-attempt limit, including failures. It does not know whether another client has consumed the project's Gemini quota. Do not delete its ledger or create a new run directory to bypass the cap. Missing credentials or exhausted quota are failures, not successful evaluations.

Preparation downloads public AMI Mix-Headset recordings as needed. Transcription uses local Whisper small and pyannote community-1, including 300 seconds of surrounding audio per side for speaker context. Extraction uses the configured Gemini 2.5 Flash key. Credentials stay in the runtime `.env`; they are never copied into evaluation artifacts.

`outputs/day09` under the environment root retains:

- `freeze.json`, `provenance.json`, `gold.json`: pre-inference settings, source hashes, recording/reference provenance, structured reference.
- `*.reference.json`, `*.transcript.json`, `*.wer.json`, `*.timing.json`: human lexical references, real ASR/diarization outputs, normalized WER counts, timing.
- `*.actions.json`, `*.decisions.json`, `*.qa.json`: exact application predictions used for scoring.
- `*.integrity.json`: exact source-reference checks, distinct from semantic correctness.
- `calls/*.json`, `request_ledger.json`: cached raw model responses and all attempts.
- `metrics.json`: recomputed aggregate and per-case results with denominators.

`day09_adjudication.json` maps each prediction to at most one reference item with a reason; unmatched references become false negatives. Every question receives full, partial, or incorrect credit. Reviews are tied to exact prediction hashes. Scoring rejects duplicate matches, missing reviews, changed outputs and changed frozen source. When modifying application code later, retain the frozen source snapshot to reproduce this evaluation separately.

## Data attribution

AMI Meeting Corpus, AMI Consortium / University of Edinburgh. Public manual annotations v1.6.2 and Mix-Headset audio from the [AMI download site](https://groups.inf.ed.ac.uk/ami/download/). Dataset license recorded by this project: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Exact audio URLs and SHA-256 hashes are in the runtime provenance file. Structured task labels and QA expectations are project annotations; they are not official AMI labels.
