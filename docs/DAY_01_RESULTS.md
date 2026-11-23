# Day 1 model selection results

Completed 2026-11-13. Source: locally executed benchmark, not vendor-reported scores.

## Corrected benchmark (version 2)

Three 60-second ES2002a development clips: 60-120, 600-660, and 900-960 seconds. Total 180 seconds; 466 normalized reference words. Human reference: AMI manual annotations v1.6.2. The held-out ES2004a meeting was not transcribed for model selection.

| Whisper model | Word errors | Normalized WER | Processing seconds | Real-time factor |
| --- | ---: | ---: | ---: | ---: |
| tiny | 213 | 45.71% | 9.22 | 0.051 |
| base | 130 | 27.90% | 16.26 | 0.090 |
| small | 117 | 25.11% | 52.34 | 0.291 |

Processing time excludes model download/loading and includes per-clip preprocessing. All models were cached for this corrected run. A real-time factor of 0.291 means 0.291 processing seconds per audio second on these clips; full-recording throughput is not yet established.

Selected `small` for initial accuracy, with `base` available as the faster alternative. Small improves WER by 2.79 percentage points versus base while taking about 3.2 times as long on these clips. This is a provisional choice from a small sample, not a claim that small always performs better.

## Reproducible settings
- Python 3.11.18; openai-whisper 20250625; torch 2.9.1+cpu.
- CPU, four Torch threads, fp16 disabled.
- Language English, transcription task, temperature zero, previous-text conditioning disabled.
- Whisper EnglishTextNormalizer applied equally to reference and hypothesis.
- Aggregate WER = total substitutions + deletions + insertions, divided by total reference words (not the unweighted average of clip WERs).
- Reference words selected by midpoint and serialized by onset. Overlapping speakers can make this ordering an imperfect scoring reference.

## Data-quality correction

The exploratory version included a 1080-1140 second clip. Its audio extended past the manual transcript coverage and included post-meeting speech without reference text. It was rejected on that basis, not because of model ranking. The corrected window is 900-960 seconds, and all three models were rerun. Earlier exploratory reports in outputs/day01 are not valid final comparison scores.

## Artifacts

Environment/data root: `C:\Users\shara\Projects\ai-meeting-intelligence`

- `data/provenance.json`: official source URLs and downloaded-file hashes.
- `data/manifest.csv`: full recordings and project splits.
- `data/references/*.json` and `*.txt`: manual-reference conversion.
- `data/benchmark_windows.json`: version 2 clip definitions and references.
- `outputs/day01/benchmark_tiny_base_small.json`: authoritative corrected comparison, counts, predictions, timestamps, and settings.
- `models/whisper/`: downloaded tiny/base/small weights.

Run the benchmark command in the repository README to reproduce the comparison. Timings vary by machine load.

## Limits and next work

This is Day 1 model selection only. The corpus contains overlapping speech and disfluencies, and WER remains substantial. No real-person identification, diarization quality, action extraction, decision tracking, Gemini requests, or QA correctness has been evaluated yet. Those remain in their scheduled days. AMI corpus speaker labels in references are not predictions from our application.

Day 2 will implement audio/video transcription, timestamps, and speaker diarization using the selected baseline. The diarization model's access conditions and token must be configured before its inference can be verified.
