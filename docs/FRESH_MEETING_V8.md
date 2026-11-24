# Fresh meeting check: ES2009a

Completed on 2026-11-24 after a transient 503 and one transport failure. Task intent: **4 TP, 1 FP, 0 FN; precision 80%, recall 100%, F1 88.89%**. WER: **16.46% (81/492 words)**. Owners and complete details each scored **2/4**. All four tasks were recovered, but a target-audience caution was incorrectly extracted as work. The first-person document owner was lost because v8 rejected the phrase `I'm`; UID ownership of user-wants reporting is ambiguous and scored incorrect under the frozen conservative rubric. The next-meeting deadline was correctly left event-relative.

Evidence: `evaluation/fresh_v8_metrics.json` and `evaluation/fresh_v8_review.json`. This result is frozen before any v9 changes prompted by these errors.

Candidate: action prompt/validation v8, published as commit `a32b01e`. No model code was changed after freezing this check. ES2009a had not appeared in the project's previous development/evaluation outputs. ES2008a was considered first but excluded before predictions because the existing reference parser encountered missing word timestamps; that exclusion limits the sample's representativeness.

Two excerpts were selected from the AMI human reference: 825–891 seconds (66 seconds) and 1300–1399 seconds (99 seconds). Four concrete tasks were annotated before transcription or extraction. This is **one meeting, not a full-meeting evaluation or a broad benchmark**. Labels and semantic adjudication are assistant-authored, not independently human-reviewed.

The first excerpt contains individual design work, reporting user wants, and a separate collective discussion of trade-offs. The second includes a commitment to document initial ideas. Vague brainstorming, passive email notifications and optional access to documents are excluded by the frozen rubric. Each delivered prediction must receive a one-to-one match or be counted as a false positive. Every omitted reference remains a false negative.

Whisper small uses beam size 5 and local speaker diarization with no extra context outside the selected intervals, matching the previous unseen experiment. Model inference receives only the ASR transcript, never the human reference or gold tasks. Exact citations, source fingerprints, normalized WER and semantic task matches are checked separately.

## Reproduce

Run from the matching source checkout with the runtime dependencies and credentials configured:

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$runtime\.venv\Scripts\python.exe"
& $python scripts/check_fresh_v8.py --environment-root $runtime --stage prepare
& $python scripts/check_fresh_v8.py --environment-root $runtime --stage transcribe
& $python scripts/check_fresh_v8.py --environment-root $runtime --stage extract
& $python scripts/score_final_validation.py --environment-root $runtime --fresh-v8
```

The prepare stage freezes source/gold hashes. Audio is downloaded from a pinned AMI mirror and checked against its LFS SHA-256 and size. Reference hashes and actual source URLs are stored in runtime `outputs/day10/fresh_v8_ES2009a/provenance.json`.

The previous 20-attempt ledger is preserved. New API calls cannot start before 2026-11-23 08:00 UTC (13:30 IST), the documented Pacific-midnight daily reset boundary. The new persistent ledger is `outputs/gemini_budget/2026-11-23-pacific/request_ledger.json`, capped at 20 attempts. A calendar reset does not guarantee service availability or unused shared-project quota. [Google rate-limit documentation](https://aistudio.google.com/docs/rate-limits).

The original six-excerpt v7 score remains unchanged. With only four gold tasks, recall moves in 25-percentage-point steps; even a perfect result here cannot establish 85–90% recall across other meetings.
