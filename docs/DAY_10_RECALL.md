# Action recall target: 85–90%

Work on 2026-11-22 found a promising way to recover missing audio evidence, but **measured end-to-end action recall remains 80% (4/5)**. No higher action-recall score has been claimed or written into the previous evaluation reports.

## Current sample and target

The five-task development sample moves in 20-percentage-point steps: four correct tasks means 80%, five means 100%. It cannot establish an 85–90% result. At least 20 reference tasks are needed for that numerical granularity (17/20 = 85%, 18/20 = 90%); substantially more data is needed for a reliable generalization estimate. Precision, owner correctness and task-detail accuracy must also be reported, so extra unsupported tasks cannot be used to manufacture a higher recall score.

## Local diagnostic

The remaining missed task is components work assigned to the Industrial Designer. The original ASR omitted components. A 30-second crop of IS1003b, 1555–1585 seconds, was re-transcribed with the installed Whisper small model. No reference text, expected task, vocabulary hint or initial prompt was supplied to Whisper. Human reference text was used only to score the resulting predictions.

| Method on this known window | WER | Errors / reference words | Local inference time |
|---|---:|---:|---:|
| Original transcript, words selected by timestamp midpoint | 40.74% | 22/54 | Not separately timed |
| Fresh 30-second crop, greedy decoding | 35.19% | 19/54 | 22.39 s |
| Same crop, beam size 5 | **24.07%** | 13/54 | 38.27 s |

The greedy recheck recovered component but distorted the role name. Beam search recovered both industrial designer and component, plus the interface assignment. This is promising audio evidence, **not proof that action extraction will correctly recover the missing task**. Timing excludes model loading and diarization. Cropping and decoding both differ from the original long-window run; the crop comparison also has timestamp-boundary differences. This single deliberately chosen error window is development evidence, not a global WER benchmark.

## Implementation

The transcription CLI and Python pipeline now accept optional `--beam-size 5` / `beam_size=5`. Beam search was exercised against the real installed Whisper model in the diagnostic. Integration tests verify forwarding to Whisper and preserving existing timestamp/speaker behavior. Invalid values fail before audio/model loading. Output warnings record explicit beam size.

The default remains unchanged, including web uploads. A single diagnostic improvement does not justify silently changing all uploads or auto-replacing saved transcripts. Beam search adds processing time and can perform worse on other recordings.

Example from the source repository (choose a new output directory):

```powershell
$envRoot = 'C:/Users/shara/Projects/ai-meeting-intelligence'
& "$envRoot/.venv/Scripts/python.exe" -m meeting_intelligence recording.wav --environment-root $envRoot --output "$envRoot/outputs/beam-review" --beam-size 5
```

**176 tests passed** in the final regression run. No Gemini calls were made for this audio check; the previously planned daily allowance had already been used. Original Day 9 and action-development scores remain unchanged.

## Validation still required

1. Run real action extraction on the recovered audio transcript when Gemini quota is available. Preserve speaker uncertainty and compare against the same frozen task; do not insert an action manually from the reference.
2. Prepare a separate set of previously unseen meetings containing at least 20 reviewed reference tasks. Freeze labels and task matching before model inference. Include implicit commitments, role assignments, overlap, concrete follow-up requests and negative examples.
3. Freeze candidate decoding/extraction settings. Evaluate both precision and recall, plus owner/detail errors. Keep this diagnostic and all earlier development examples separate from the new test set.
4. Claim 85–90% only if the new measured results support it. Retain failures and uncertainty; do not relax the rubric after predictions.

## Evidence

- [Diagnostic measurements and exact text](../evaluation/day10_recall_audio_probe.json)
- [Reproducible local probe](../scripts/probe_recall_audio.py)
- Runtime raw decoding outputs: `C:/Users/shara/Projects/ai-meeting-intelligence/outputs/day10/recall_audio_probe`
- [Previous action-improvement results and their limitations](DAY_10_IMPROVEMENTS.md)
