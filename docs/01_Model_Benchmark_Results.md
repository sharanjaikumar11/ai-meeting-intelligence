# Speech to Text Model Benchmark Report

This report summarises the saved Whisper benchmark on three AMI meeting excerpts. Whisper Tiny, Base and Small were tested on the same audio and scored against the same human reference. Later extraction improvements are reported separately and do not change these model-comparison results.

## 1. Benchmark overview

| Measure | Benchmark setup |
|---|---|
| Dataset | AMI Meeting Corpus, meeting ES2002a |
| Input | Three headset-mix audio excerpts |
| Excerpt intervals | 60–120, 600–660 and 900–960 seconds |
| Duration per excerpt | 60 seconds |
| Unique audio duration | 180 seconds — 3 minutes |
| Scored reference words | 466 after text normalization |
| Models compared | Whisper Tiny, Base and Small |
| Mode of run | Local CPU; four Torch threads; FP16 disabled |
| Language and task | English transcription |
| Decoding | Temperature 0; previous-text conditioning disabled |
| Software | Python 3.11.18, openai-whisper 20250625, PyTorch 2.9.1+cpu |
| Benchmark date | 13 November 2026 |

Each model processed all three excerpts, giving nine model–excerpt runs. The unique dataset contains 180 seconds of audio; the cumulative audio processed across all three models is 540 seconds. GPU inference was not used.

## 2. Model results

| Model | Approximate parameters | Mode of run | Completed excerpts | Word errors | Word Error Rate |
|---|---:|---|---:|---:|---:|
| Whisper Tiny | 39 million | CPU | 3/3 | 213/466 | 45.71% |
| Whisper Base | 74 million | CPU | 3/3 | 130/466 | 27.90% |
| Whisper Small | 244 million | CPU | 3/3 | 117/466 | **25.11%** |

All models completed the benchmark. Completion means a saved transcript was produced; it does not mean the transcript was correct. Parameter counts are the documented approximate model sizes, not a new parameter-count measurement.

## 3. Inference time per model

| Model | Mean time per 60-second excerpt | Total inference for three excerpts | Model loading time | Loading plus inference | Real-time factor |
|---|---:|---:|---:|---:|---:|
| Whisper Tiny | 3.07 s | 9.22 s | 0.29 s | 9.51 s | 0.051 |
| Whisper Base | 5.42 s | 16.26 s | 0.54 s | 16.79 s | 0.090 |
| Whisper Small | 17.45 s | 52.34 s | 2.09 s | 54.43 s | 0.291 |

**Total inference across the three models: 77.82 seconds.**

Total recorded model loading was 2.91 seconds. Adding loading to inference gives **80.74 seconds** of recorded work. This sum is not a measurement of the complete benchmark script's wall-clock duration: scoring, file writing and other work outside these timers are not included.

Inference time was measured around each `model.transcribe(...)` call. It includes preprocessing performed inside that call, but excludes model loading, model downloads, speaker diarization, Gemini requests, evaluation and manual review. The model weights were already cached for this corrected run. Totals are calculated from unrounded measurements.

Real-time factor means processing seconds divided by audio seconds. Small's factor of 0.291 means it took approximately 0.291 seconds to process one second of audio in this benchmark. It does not describe the complete meeting-intelligence pipeline.

## 4. Timing and WER for each excerpt

| Excerpt in ES2002a | Tiny time | Tiny WER | Base time | Base WER | Small time | Small WER |
|---|---:|---:|---:|---:|---:|---:|
| 60–120 seconds | 3.23 s | 27.40% | 5.50 s | 13.70% | 18.32 s | 8.90% |
| 600–660 seconds | 2.76 s | 106.02% | 4.24 s | 21.69% | 11.26 s | 22.89% |
| 900–960 seconds | 3.24 s | 35.86% | 6.51 s | 38.82% | 22.76 s | 35.86% |

Tiny repeated phrases in the second excerpt, producing many inserted words. WER can exceed 100% when insertions make the error count larger than the reference word count; this value is not a percentage of correctly recognised words.

## 5. Metrics explained simply

| Measure | Meaning |
|---|---|
| Substitution | A spoken reference word is replaced with a different word |
| Deletion | A reference word is missing from the transcript |
| Insertion | The transcript contains an extra word |
| WER | `(substitutions + deletions + insertions) / reference words`; lower is better |
| Real-time factor | Processing time divided by audio duration; lower is faster |

| Model | Substitutions | Deletions | Insertions | Total word errors |
|---|---:|---:|---:|---:|
| Tiny | 65 | 82 | 66 | 213 |
| Base | 23 | 96 | 11 | 130 |
| Small | 35 | 68 | 14 | 117 |

The Whisper EnglishTextNormalizer was applied to both predictions and references. The overall WER uses pooled word counts, not an unweighted average of the three excerpt percentages. CER and text-similarity scores were not part of this benchmark.

## 6. Other models used in the application

| Model | Purpose | Mode of run | Benchmark status |
|---|---|---|---|
| pyannote speaker-diarization-community-1 | Estimate who spoke when | Local CPU | Integrated and tested; no separate model comparison, standalone latency or diarization-error-rate benchmark |
| Gemini 2.5 Flash | Summaries, actions, decisions and meeting QA | Hosted API | Evaluated within the application; no comparison against alternative LLMs and no reliable standalone request-latency measurements saved |

These components are not additional Whisper benchmark candidates. Their application results are in the separate evaluation report.

## 7. Source and scope

Source: runtime `outputs/day01/benchmark_tiny_base_small.json`, corrected benchmark version 2. The benchmark script and interpretation are documented in [Day 1 model selection results](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs/DAY_01_RESULTS.md).

An earlier 1080–1140-second excerpt extended beyond manual-reference coverage. It was replaced with 900–960 seconds and all three models were rerun. Those earlier exploratory results are excluded here. The comparison covers one meeting and three short excerpts, not a general benchmark of all meeting conditions.
