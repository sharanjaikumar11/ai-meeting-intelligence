# Day 2: audio/video transcription, timestamps, and speaker identification

Status: completed 2026-11-13. Real audio/video transcription and Community-1 speaker diarization passed functional checks. Automatic speaker counting detected 3 speakers versus 4 in the reference excerpt; this quality limitation remains for later testing and evaluation.

## Implemented

- Local audio/video input using FFmpeg and ffprobe; rejects corrupt files and video without audio.
- 16-kHz mono audio extraction, with optional source start/duration.
- Whisper Small CPU transcription with segment and word timestamps.
- pyannote Community-1 adapter for normal and exclusive speaker turns.
- Word assignment by temporal overlap; split transcript segments at speaker changes.
- Unassigned speaker for timing gaps or tied overlap, rather than guessing a nearby speaker.
- Overlapping-speech flags and retained nonexclusive turns.
- Optional user-provided speaker-name mapping; speaker IDs alone are not real names.
- Pydantic-validated transcript JSON plus timestamped text export.
- All timestamps use seconds relative to the original input file, including when a subsection is processed.

## Run from the source repository

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence `
  "$envRoot\data\recordings\ES2002a.Mix-Headset.wav" `
  --environment-root $envRoot `
  --output "$envRoot\outputs\day02\speaker_demo" `
  --start 60 --duration 120
```

The output directory must be new; an existing result is never overwritten. Omit start/duration to process the entire file. Audio or video paths are accepted. English is the default; use `--language auto` for language detection or an explicit supported language code. Use `--num-speakers` only if that count is known.

For transcription-only execution while model access is pending, explicitly add `--skip-diarization`. Output then has `diarization_status: "skipped"`, empty speaker lists, and null speaker assignments. It is not a completed speaker-labelled result.

## Configure speaker model access

1. Sign in and review the access conditions at https://huggingface.co/pyannote/speaker-diarization-community-1.
2. Accept the conditions if you agree, and create a token with permission to read the gated model.
3. Copy the environment directory's `.env.example` to `.env` and set `HF_TOKEN` locally. Do not send the token in chat or commit it.
4. Run the command above. Model files are cached under `models/huggingface` in the environment directory.

The application uses the token only to load the model. Audio processing runs locally. A Gemini key is not needed for Day 2.

Once speaker IDs are detected, a user-confirmed mapping may be supplied with `--speaker-names names.json`, for example `{"SPEAKER_00": "Alice"}`. Unmapped speakers retain their IDs. Unknown IDs are rejected. Speaker numbering is local to each processed recording or excerpt and is not an identity across meetings.

## Output contract

`transcript.json` contains source and processed duration, language, model names, diarization status, full ASR text, speakers, timestamped segments/words, regular/exclusive diarization turns, and warnings. Every segment has a stable ID within that output and a reference to its original ASR segment. Word probability is Whisper's token-based estimate, not calibrated confidence in the full transcript or speaker identity.

`transcript.txt` is a readable view with `[HH:MM:SS.mmm - HH:MM:SS.mmm] SPEAKER: text` lines. Missing speaker assignments are explicitly `UNASSIGNED`.

## Verification

17 tests cover alignment, ambiguity, overlap, timestamp offset/rounding, schema validation, missing token handling, real FFmpeg video extraction, corrupt/missing-audio rejection, output preservation, and pipeline integration with mocked model outputs. The mocked integration test verifies wiring only; it is not evidence that the gated diarization model has run.

```powershell
$env:MEETING_ENV_ROOT = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$env:MEETING_ENV_ROOT\.venv\Scripts\python.exe" -m pytest tests/test_day02.py -q
```

Real transcription and speaker-diarization demonstrations and their verification are recorded in DAY_02_RESULTS.md. The held-out ES2004a meeting is not used for implementation debugging. Run `scripts/verify_day02.py --environment-root ROOT` to validate the saved demonstration outputs and reference speaker count.
