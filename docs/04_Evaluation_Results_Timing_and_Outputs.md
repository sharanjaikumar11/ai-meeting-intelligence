# Meeting Intelligence Evaluation and Final Results

This report covers the final improved action extractor, the fresh-meeting check, speech metrics, recorded processing times and saved outputs. The main comparison uses the same 20 reference tasks before and after improvement. Later retests are kept separate from the original unseen results.

## 1. Final improved scores

The final action-extraction version is **v9**. On the six-meeting, 20-task development set, it correctly recovered 15 tasks, produced two extra tasks and missed five reference tasks.

| Measure | Final v9 result | Meaning |
|---|---:|---|
| Action precision | **88.24%** | 15 correct tasks out of 17 predicted tasks |
| Action recall | **75.00%** | 15 recovered tasks out of 20 reference tasks |
| Action F1 | **81.08%** | Combined precision and recall measure |
| Correct owners on matched tasks | **86.67% (13/15)** | Owner correctness among correctly matched tasks only |
| Complete/correct details on matched tasks | **86.67% (13/15)** | Task-detail correctness among matched tasks only |
| WER on these saved transcripts | **21.44% (300/1,399)** | Word errors relative to the human transcript |
| Excerpts with delivered v9 action outputs | **6/6** | Processing completion, separate from task accuracy |

These cases were inspected during improvement, so this is a development result. It must not be presented as a new unseen score or as 75% accuracy for every output field.

## 2. Before and after improvement

| Measure | Original v7 baseline | Final v9 |
|---|---:|---:|
| Reference tasks | 20 | 20 |
| Correct tasks | 11 | 15 |
| Extra tasks | 1 | 2 |
| Missed tasks | 9 | 5 |
| Precision | 91.67% | 88.24% |
| Recall | 55.00% | 75.00% |
| F1 | 68.75% | 81.08% |
| Correct owners among matched tasks | 8/11 | 13/15 |
| Complete/correct details among matched tasks | 8/11 | 13/15 |

Recall improved by **20.00 percentage points**, and F1 improved by **12.33 percentage points**. Precision decreased by **3.43 percentage points** because the revised run returned more correct tasks but also one additional false positive.

The original v7 result included a failed TS3006a extraction. Its four reference tasks were counted as missed, not removed from evaluation. All six v9 runs returned action outputs. The audio transcripts were reused unchanged, so these action-extraction changes did not alter WER.

## 3. Results for each evaluated excerpt

| Meeting and interval | Reference tasks | Correct | Extra | Missed | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ES2006a, 1235–1275 s | 3 | 3 | 0 | 0 | 100% | 100% |
| ES2007a, 1100–1199 s | 3 | 3 | 0 | 0 | 100% | 100% |
| ES2010a, 575–639 s | 3 | 2 | 0 | 1 | 66.67% | 80% |
| ES2011a, 1015–1105 s | 3 | 2 | 1 | 1 | 66.67% | 66.67% |
| IS1004a, 700–767 s | 4 | 4 | 0 | 0 | 100% | 100% |
| TS3006a, 807–1000 s | 4 | 1 | 1 | 3 | 25% | 33.33% |
| **Total** | **20** | **15** | **2** | **5** | **75%** | **81.08%** |

Matching task intent does not establish correct ownership. For example, ES2007a recovered all three task intents but incorrectly attributed the button-design task to marketing. The owner scores above preserve that error.

## 4. Fresh meeting and later retest

ES2009a was not previously used for development. Four tasks were annotated before inference across two excerpts: 825–891 seconds and 1300–1399 seconds. The initial v8 result is the fresh check. Once those errors were reviewed, the v9 rerun became a development retest.

| Measure | Initial fresh v8 check | Final v9 retest |
|---|---:|---:|
| Reference tasks | 4 | 4 |
| Correct / extra / missed tasks | 4 / 1 / 0 | 4 / 0 / 0 |
| Precision | 80% | 100% |
| Recall | 100% | 100% |
| F1 | 88.89% | 100% |
| Correct owners | 2/4 | 3/4 |
| Complete/correct details | 2/4 | 3/4 |
| WER | 16.46% (81/492 words) | Unchanged |

The revised run removed a general audience caution and restored the explicit first-person document owner. A UID attribution remains ambiguous under the frozen owner rubric, and one task description still omits trade-off detail.

The 100% task result covers four tasks, not the full meeting or a broad dataset. It is not evidence that the application has reached 85–90% recall on general unseen meetings.

## 5. Evaluation method

| Check | Method |
|---|---|
| Speech to text | Normalize reference and prediction with Whisper EnglishTextNormalizer; calculate pooled substitutions, deletions and insertions using JiWER |
| Action items | One-to-one semantic matching to frozen reference tasks; extra/duplicate outputs are false positives and omissions are false negatives |
| Owners and task details | Score separately on matched tasks; a correct task can still have an incorrect owner or incomplete detail |
| Decisions | Match final agreed decisions against the reference; do not treat proposals or unresolved discussions as final agreements |
| QA | Review the whole answer for correctness and support; a wrong factual addition can make an otherwise useful answer incorrect |
| Evidence | Verify source fingerprint, segment IDs, exact quotes, timestamps and speaker metadata |

Precision is `TP / (TP + FP)`, recall is `TP / (TP + FN)`, and F1 is `2 × TP / (2 × TP + FP + FN)`. Structured reference labels and semantic reviews were authored by the assistant using AMI human transcripts; they were not independently reviewed by a second human annotator.

## 6. Recorded inference and processing time

### 6.1 Six-excerpt transcription pipeline

These are measured elapsed times for **audio preparation, model loading, Whisper transcription, pyannote diarization, alignment and transcript saving together**. They are not isolated Whisper or Gemini inference times. The run used Whisper Small with beam size 5 and no extra diarization context outside each excerpt.

| Meeting and interval | Audio duration | Recorded pipeline time | Approximate minutes |
|---|---:|---:|---:|
| ES2006a, 1235–1275 s | 40 s | 113.37 s | 1.89 |
| ES2007a, 1100–1199 s | 99 s | 242.11 s | 4.04 |
| ES2010a, 575–639 s | 64 s | 150.07 s | 2.50 |
| ES2011a, 1015–1105 s | 90 s | 206.47 s | 3.44 |
| IS1004a, 700–767 s | 67 s | 180.48 s | 3.01 |
| TS3006a, 807–1000 s | 193 s | 365.00 s | 6.08 |
| **Total** | **553 s — 9.22 min** | **1,257.51 s** | **20.96 min** |

The v9 action rerun reused these transcripts. It did not repeat the 1,257.51 seconds of audio processing. This timing is attached to the source-transcript run, not newly incurred v9 transcription time.

## 7. Saved outputs and examples

### 7.1 Actual improved action output

The following selected fields come from the saved v9 output for ES2009a, 1300–1399 seconds. This is an excerpt of the response, not its complete schema:

```json
{
  "id": "action_0000",
  "task": "put these initial ideas in the project documents",
  "assignment_type": "commitment",
  "owner": {
    "kind": "self",
    "mention": "I'm",
    "responsible_person": null,
    "speaker_id": "SPEAKER_00"
  },
  "deadline": {
    "text": null,
    "date_iso": null,
    "resolution": "missing"
  }
}
```

The full output also contains the cited transcript segments, exact quotes and timestamps. The person's real name remains unknown; the application does not convert a speaker cluster into an invented name.

### 7.2 Live meeting assistant output

Question: **What is the purpose of this meeting?**

Saved answer: “The purpose of the meeting is to design a new remote control. The new remote control is supposed to be original, trendy, and user-friendly.”

The answer status was `answered`, and its supporting transcript citations were verified. The 60-second public AMI MP4 had already completed transcription, speaker labeling, summary, action extraction, decision tracking and a matching JSON download. QA was resumed and completed on 24 November 2026. Its saved upload-stage actions predate v9; this demo is separate from the eight-excerpt v9 action test.

### 7.3 Output locations

| Record | Location |
|---|---|
| Improved action metrics and review | `evaluation/action_extraction/final_metrics.json`, `evaluation/action_extraction/final_review.json` |
| Fresh v8 metrics and review | `evaluation/fresh_meeting/initial_metrics.json`, `evaluation/fresh_meeting/initial_review.json` |
| Original 20-task baseline | `evaluation/action_extraction/baseline_metrics.json` |
| Required decision and QA aggregate metrics | `evaluation/decision_qa/metrics.json` |
| Saved v9 action outputs | Runtime `outputs/day10/release_v9/` |
| Source transcription timing files | Runtime `outputs/day10/final_2026-11-23/*.timing.json` |
| Demo combined JSON | Runtime `outputs/day10/final_2026-11-23/demo.result.json` |
| Demo QA and verification record | Runtime `outputs/day10/final_2026-11-23/demo.json` |
