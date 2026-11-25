# Why Whisper Small Was Selected

## 1. Selection rationale

Whisper Small was selected as the speech-to-text model because it achieved the lowest overall Word Error Rate among the three candidates tested on the project's CPU environment. The choice prioritised transcription quality, with processing time considered as an explicit trade-off.

This is the selected speech-recognition model. Speaker diarization and meeting-information extraction use separate components: pyannote Community-1 and Gemini 2.5 Flash.

## 2. Evaluation scope

The comparison used three 60-second development excerpts from AMI meeting ES2002a: 180 seconds of audio and 466 normalized reference words. Tiny, Base and Small used the same excerpts, references and scoring method. The held-out ES2004a meeting was not used to select the Whisper model.

Execution used local CPU inference with four Torch threads and FP16 disabled. All three models produced saved transcripts for every excerpt.

## 3. Measured results

| Measure | Whisper Small result | Meaning |
|---|---:|---|
| Completed excerpts | 3/3 | Produced a transcript for every benchmark excerpt |
| Word errors | 117/466 | Substitutions, deletions and insertions pooled across the reference words |
| Word Error Rate | **25.11%** | Lowest overall WER among the three tested models |
| Mean inference time | 17.45 seconds per 60-second excerpt | Average measured transcription-call duration |
| Total inference time | 52.34 seconds | Sum for the three excerpts, excluding model loading |
| Model loading time | 2.09 seconds | Recorded separately with weights already cached |
| Loading plus inference | 54.43 seconds | Sum of those two measured components |
| Real-time factor | 0.291 | Processing seconds per audio second in this benchmark |

## 4. Why these results supported the choice

### 4.1 Lowest overall word error rate

Small achieved 25.11% WER, compared with Base at 27.90% and Tiny at 45.71%. Small made 13 fewer word errors than Base and 96 fewer than Tiny across the same reference.

The improvement over Base was **2.79 percentage points**, approximately a 10% relative reduction in word errors. This matters because missing or incorrect words can affect downstream task names, responsible persons, dates and decisions.

Lower WER does not guarantee correct action extraction. The project separately evaluates those downstream outputs.

### 4.2 Worked on the available environment

Small completed all three excerpts on the installed CPU configuration. CUDA was unavailable in the tested environment, so the selection was based on the actual CPU run rather than assumed GPU performance.

### 4.3 The speed cost was measured

| Comparison | Accuracy difference | Processing-time difference |
|---|---|---|
| Small versus Base | 2.79 percentage points lower WER | 52.34 s versus 16.26 s; Small took about 3.22 times as long |
| Small versus Tiny | 20.60 percentage points lower WER | 52.34 s versus 9.22 s; Small took about 5.67 times as long |

Small was not the fastest model. Base remains the measured faster alternative when shorter processing time is more important than the modest accuracy improvement in this sample.

### 4.4 The result was considered across the full comparison

Small did not win every excerpt. Base performed slightly better on the 600–660-second excerpt, and Tiny and Small had equal WER on 900–960 seconds. The decision used pooled results across all three excerpts rather than selecting a model from one favourable case.

## 5. Selected configuration in the application

| Component | Selected model or setting | Reason |
|---|---|---|
| Speech recognition | Whisper Small | Best pooled WER in the measured comparison |
| Speaker diarization | pyannote Community-1 | Supplies speaker-turn estimates that Whisper alone does not provide |
| Information extraction and QA | Gemini 2.5 Flash | Configured LLM used for structured outputs and transcript-grounded review |
| Local execution | CPU; four Torch threads; FP16 disabled | Matches the verified environment |
| Transcript timing | Segment and word timestamps | Supports speaker alignment and evidence links |

Pyannote and Gemini were integrated and tested, but they were not selected through a head-to-head benchmark against alternative diarization models or LLMs. No comparative “best model” claim is made for them.

## 6. Later decoding improvement

An optional beam-size-5 setting was added and tested on a known 30-second error window. The same model with greedy decoding produced 35.19% WER in 22.39 seconds; beam size 5 produced 24.07% WER in 38.27 seconds. These timings exclude model loading and diarization.

This was a targeted development diagnostic, not a new comparison of Whisper model sizes. The later evaluation excerpts used beam size 5. Ordinary web uploads retain the existing default decoding unless the implementation is explicitly changed; the optional CLI setting does not automatically alter web-upload behaviour.

## 7. Evidence and interpretation

The choice is supported by the saved [model-selection report](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs/DAY_01_RESULTS.md) and runtime `outputs/day01/benchmark_tiny_base_small.json`. The decoding diagnostic is recorded in [the recall audio probe](https://github.com/sharanjaikumar11/ai-meeting-intelligence/blob/main/evaluation/speech/decoding_diagnostic.json).

Small is the preferred model for this project's tested configuration. The sample is too small to establish that it is universally the best Whisper model or to predict full-meeting processing speed.
