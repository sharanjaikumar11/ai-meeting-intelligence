# Evaluation

Measured evidence for the AI Meeting Intelligence Agent. Start with the results table, then use the references and semantic reviews to inspect individual errors. No scores were changed during this reorganization.

## Results at a glance

| Evaluation | Sample | Result | Interpretation |
|---|---|---|---|
| Speech model selection | Three 60-second excerpts; 466 reference words | Tiny WER 45.71%; Base 27.90%; Small 25.11% | Same audio and settings; Small selected for lowest pooled WER |
| Final action extraction | Six excerpts; 20 reference tasks | Precision 88.24%; recall 75%; F1 81.08% | Development regression: 15 correct, 2 extra, 5 missed |
| Action baseline | Same six excerpts and 20 tasks | Precision 91.67%; recall 55%; F1 68.75% | Frozen v7 result before these cases were used for tuning |
| Fresh-meeting check | Two excerpts from ES2009a; four tasks | Precision 80%; recall 100%; F1 88.89% | Initial v8 result, before reviewing this meeting's errors |
| Fresh-meeting retest | Same four tasks | Precision, recall and F1 100% | v9 development retest; owners and details each correct for 3/4 |
| Decision extraction | Original three-excerpt pilot; three reference decisions | Precision 100%; recall 33.33%; F1 50% | Only one correct prediction; not a broad precision estimate |
| Question answering | Six fixed questions in the original pilot | 4/6 fully correct: 66.67% | Latest measured aggregate; not rerun after action improvements |

On the six-excerpt set, owners and task details were each correct for 13/15 matched tasks (86.67%). WER was 21.44% on unchanged transcripts. The 20-point recall gain is a same-set development improvement, not evidence of 85-90% unseen recall.

## Evidence layout

| Directory | Contents | Why retained |
|---|---|---|
| [speech](speech/) | Model benchmark and targeted decoding diagnostic | Supports Whisper selection, WER and recorded inference times |
| [action_extraction](action_extraction/) | Shared reference, baseline metrics/review, final metrics/review | Supports the controlled before/after task comparison |
| [fresh_meeting](fresh_meeting/) | Frozen reference and initial metrics/review | Preserves the fresh test separately from the later tuned retest |
| [decision_qa](decision_qa/) | Pilot reference, metrics and semantic review | Preserves the measured decision and QA results required by the assignment |
| [manifest.json](manifest.json) | SHA-256 and original location for each retained artifact | Confirms relocation did not alter recorded evidence |

`action_extraction/final_metrics.json` includes both the six-excerpt regression and the ES2009a retest. Its historical keys `day10_unseen` and `fresh_v8` are provenance identifiers; the first does not mean the final tuned result is unseen. Original identifiers and embedded historical paths remain unchanged inside frozen JSON to preserve review hashes. Use the manifest to map old filenames to their current locations.

## Method

- **Speech:** Whisper EnglishTextNormalizer on reference and prediction; pooled word errors using JiWER. WER = (substitutions + deletions + insertions) / reference words.
- **Actions and decisions:** One-to-one semantic matching against frozen references. Extra predictions are false positives; missing reference items are false negatives. Failed extraction is not excluded from the denominator.
- **Precision / recall / F1:** TP / (TP + FP), TP / (TP + FN), and 2TP / (2TP + FP + FN).
- **Owners and details:** Evaluated separately on matched tasks. A correct task does not imply a correct owner or complete scope.
- **QA:** Whole-answer correctness and evidential support. A false factual addition can make an answer incorrect.
- **Evidence integrity:** Exact output hashes, segment IDs, quotes, timestamps and source fingerprints. Citation integrity is not semantic correctness.

The structured labels and reviews were assistant-authored from AMI human transcripts, without independent human adjudication. These are small, purposive samples, not an official AMI benchmark. No aggregate diarization error rate or positive deadline-change accuracy has been established.

## Reproduce the final scores

Run from the source checkout in PowerShell. The existing local runtime must contain the saved transcripts, predictions and source manifest; a GitHub clone alone does not contain those large runtime outputs.

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$runtime\.venv\Scripts\python.exe"
& $python scripts/score_release_v9.py --environment-root $runtime
```

This scorer makes **no model/API calls**. It validates source, reference, transcript and prediction hashes, checks evidence, and recomputes the final action metrics from the semantic reviews. It writes `action_extraction/final_metrics.json`. Missing runtime artifacts or changed source should fail explicitly; do not disable integrity checks to reproduce a score.

The dated inference and pilot scripts under `scripts/` are historical experiment runners. Their original paths and frozen source dependencies are preserved intentionally; use the matching archived source/bundle, not the current reorganized checkout, to reproduce those experiments. [Preserved experiment source and artifacts](https://github.com/sharanjaikumar11/ai-meeting-intelligence/tree/5d957d1). Superseded interim experiments and incomplete review progress were removed from the current evaluation folder; Git history retains them.

## Timing and interpretation

The speech benchmark records transcription-call time separately from model loading. Whisper Small took 52.34 seconds for 180 seconds of audio; all three models together used 77.82 seconds of transcription time. These exclude diarization and Gemini.

The six-excerpt audio pipeline took 1,257.51 seconds for 553 seconds of audio, including preparation, loading, transcription, diarization, alignment and transcript saving. v9 reused these transcripts. Standalone Gemini latency and full upload-to-answer time were not recorded reliably. Different recordings, decoding settings and timer scopes must not be compared as controlled speed improvements.

See [the final results report](../docs/04_Evaluation_Results_Timing_and_Outputs.md) for per-case results and saved output examples, and [the model benchmark report](../docs/01_Model_Benchmark_Results.md) for per-model timings.

## Data provenance

Public English recordings and human transcripts come from the [AMI Meeting Corpus](https://groups.inf.ed.ac.uk/ami/download/). Manual annotations version 1.6.2 and Mix-Headset audio were used; the project records the dataset license as [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Audio URLs and checksums are stored in runtime provenance. Structured task and QA references are project annotations, not official AMI labels. Credentials, recordings and model caches are not published in this folder.
