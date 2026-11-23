# Day 2 verification results

Date: 2026-11-13.

Update 2026-11-16: the original merge below is corrected in the context-assisted development run (four automatic speaker IDs, 252/255 correct reference-word midpoint assignments). See [quality follow-up](DAYS_01_05_QUALITY_REVIEW.md) for comparison and residual errors.

## Automated checks

17 tests passed. Coverage includes speaker-change splitting, no nearest-speaker guessing in gaps, tied assignment, zero-duration word boundaries, genuine overlapping speech, original-file timestamp offsets, name mapping, invalid timestamps, output schema constraints, corrupt/no-audio video rejection, real FFmpeg extraction, missing model access, and preservation of existing output directories.

The pipeline wiring test uses mocked ASR/diarization outputs and is explicitly labelled as such. It does not establish real diarization quality or successful model loading.

## Real audio inference

- Input: AMI ES2002a headset-mix WAV, original interval 60-180 seconds.
- Model: Whisper Small, CPU, four threads, word timestamps enabled.
- Result: 28 segments and 242 words.
- Verified output timestamps remain within original-file seconds 60-180.
- JSON validated against the application schema.
- Diarization explicitly skipped, with no invented speaker labels or names.
- Output directory: `C:\Users\shara\Projects\ai-meeting-intelligence\outputs\day02\audio_excerpt`.

## Real video inference

The test fixture combines a black video frame with AMI ES2002a audio from seconds 60-120. It is a generated input-format test, not an original AMI camera recording. Timestamps in its transcript are relative to this MP4 file (0-60 seconds).

Result: 11 segments and 130 words. Schema and timestamp bounds passed validation. Diarization was explicitly skipped.

Output directory: `C:\Users\shara\Projects\ai-meeting-intelligence\outputs\day02\video_excerpt`. Both real runs are recorded in the machine-readable `outputs/day02/validation.json`.

## Real speaker diarization

Hugging Face authentication and gated model access were verified without displaying the token. Community-1 model files were downloaded and the model ran locally on the CPU.

- Input: ES2002a, seconds 60-180; speaker count inferred automatically.
- Result: 32 transcript segments, 242 words, 3 predicted speaker IDs.
- Segment assignments: SPEAKER_00 = 18, SPEAKER_01 = 3, SPEAKER_02 = 7, UNASSIGNED = 4.
- Seven segments contain detected overlapping speech.
- Source timestamp bounds, speaker references, JSON schema, and text export passed validation.
- Manual reference contains 4 speakers in this interval. The inferred count of 3 indicates under-clustering; the displayed introductions for two different people share one predicted ID. This is a real quality limitation, not a claim of correct identification of all participants.
- Real names remain unset. The application retains anonymous speaker IDs until a user-confirmed mapping is supplied.
- Output: `C:\Users\shara\Projects\ai-meeting-intelligence\outputs\day02\speaker_demo`.

The initial no-token check also correctly exited with an actionable message before Whisper inference and produced no output. After user configuration, the real model run and transcript validation passed. Day 2 is checked off for functional implementation; speaker-count errors and unassigned speech are recorded for Days 8-9.

Machine-readable results: `outputs/day02/speaker-validation.json` and `outputs/day02/validation.json` in the environment directory. Reproduce verification with `scripts/verify_day02.py --environment-root ROOT`.

No Day 9 performance metrics or speaker-identification accuracy are claimed by these implementation checks.
