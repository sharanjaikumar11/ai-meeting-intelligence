# Day 1: Whisper study and dataset preparation

## Architecture
Whisper is a Transformer encoder-decoder speech model. Audio is converted to a log-Mel spectrogram; the encoder represents the audio and the decoder predicts tokens. Task and language tokens control transcription behavior. Use transcription, not translation, to preserve the spoken language. Timestamp output will be implemented on Day 2. Speaker diarization is separate from transcription; speaker labels alone do not establish real names.

## Model comparison
| Checkpoint | Parameters | Proposed role |
| --- | --- | --- |
| openai/whisper-tiny | 39 million | Lowest-compute comparison |
| openai/whisper-base | 74 million | Initial lower-compute baseline |
| openai/whisper-small | 244 million | Accuracy comparison candidate |

Compared tiny, base, and small on three shared 60-second development clips using four CPU threads. Selected small as the initial accuracy baseline (25.11% normalized WER); base remains the speed alternative (27.90%). Model choice is provisional until broader evaluation. See DAY_01_RESULTS.md for counts, timing, and limitations.

Sources reviewed:
- https://huggingface.co/openai/whisper-base
- https://huggingface.co/openai/whisper-small

## Verified environment
- Isolated Python 3.11.18 environment: `C:\Users\shara\Projects\ai-meeting-intelligence\.venv`.
- Intel Iris Xe graphics detected; CPU PyTorch 2.9.1 is installed and CUDA is unavailable.
- FFmpeg shared build, Whisper, pyannote.audio, Gemini SDK, FastAPI, and evaluation dependencies passed environment checks.
- Official Whisper tiny, base, and small weights downloaded, checksum-validated by Whisper's loader, and successfully used for inference.
- Large artifacts remain under the Projects directory; source and documentation remain in this repository.

## Dataset prepared
- AMI meetings ES2002a, ES2003a, ES2004a: 57.70 minutes total.
- Manual annotation conversion: 7,252 lexical words and 610 transcript segments.
- Checked timestamp bounds and exact lexical word coverage in segments.
- Split by meeting: development, validation, and held-out test respectively.
- Retained original summary/action/decision/problem annotations. Structured extraction and QA labels will be reviewed with their later modules.
- Preserved source URLs, license attribution, and SHA-256 hashes in data/provenance.json.

## Completion requirements
- [x] Read Whisper model cards and document architecture.
- [x] Identify initial comparison candidates.
- [x] Create dataset manifest and annotation checklist.
- [x] Confirm usable Python environment and compute.
- [x] Obtain meeting recordings and corpus human references.
- [x] Prepare and inspect dataset entries.
- [x] Confirm initial model selection on available hardware.

Day 1 completed on 2026-11-13. This does not mark the Day 2 transcription/diarization application or the Day 9 evaluation complete.
