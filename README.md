# AI Meeting Intelligence Agent

Convert meeting audio/video into timestamped transcripts, speaker labels, summaries, action items, decision histories and evidence-backed answers.

## Project documentation

- [Model benchmarks and inference times](docs/01_Model_Benchmark_Results.md)
- [Selected model and selection reasons](docs/02_Selected_Model_and_Reason.md)
- [Pipeline details](docs/03_Pipeline_Details.md)
- [Final evaluation, timings and outputs](docs/04_Evaluation_Results_Timing_and_Outputs.md)

The final v9 action extractor achieved **88.24% precision, 75% recall and 81.08% F1** on the same 20-task development set. Recall improved from 55%; these tuned cases are not a new unseen benchmark. The original decision and QA aggregate results remain available in `evaluation/decision_qa/metrics.json`. Model accuracy limitations remain; this is a local single-user application.

## Quick demo on the configured machine

Run from this repository in PowerShell:

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$runtime\.venv\Scripts\python.exe"
& $python -m meeting_intelligence.web --environment-root $runtime --port 8001
```

Open http://127.0.0.1:8001. Upload audio/video and start with a short excerpt. Inspect the transcript, summary, actions, decisions and supporting evidence; ask a self-contained question and download JSON. Press Ctrl+C in the terminal to stop the server.

## Setup and operation

### Tested environment

Windows, Python 3.11, CPU PyTorch 2.9.1, Whisper small, pyannote Community-1, Gemini 2.5 Flash and FFmpeg 8.1 shared libraries. Python dependencies are pinned in the repository's `requirements.lock.txt`; development tools add Ruff in `requirements-dev.txt`. Node dependencies are pinned in `package-lock.json`. These pins were collected from the working environment, not from a separate clean-machine installation.

### Install

Run in PowerShell from the source checkout. Choose a runtime directory with space for models and recordings:

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
New-Item -ItemType Directory -Force $runtime
py -3.11 -m venv "$runtime\.venv"
$python = "$runtime\.venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install torch==2.9.1+cpu torchaudio==2.9.1+cpu --index-url https://download.pytorch.org/whl/cpu
& $python -m pip install -r requirements-dev.txt
& $python -m pip check
```

Install a Windows x64 shared FFmpeg build containing `ffmpeg.exe`, `ffprobe.exe` and its DLLs under `$runtime\tools\ffmpeg\<build-name>\bin`. The tested build is `ffmpeg-n8.1-latest-win64-lgpl-shared-8.1`. The media pipeline also accepts FFmpeg on PATH, but the environment smoke test expects the bundled directory above. A static executable alone does not supply TorchCodec's required shared libraries.

Copy `.env.example` to `$runtime\.env` only if that file does not already exist, then edit it locally. Set `HF_TOKEN`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL`. Accept the access conditions for `pyannote/speaker-diarization-community-1` using the same Hugging Face account as the token. Do not commit credentials. First inference downloads model weights and requires internet access; Gemini analysis requires internet access and available project quota.

```powershell
if (-not (Test-Path "$runtime\.env")) { Copy-Item .env.example "$runtime\.env" }
& $python environment_smoke_test.py --environment-root $runtime
npm ci
& scripts/check.ps1 -Python $python -EnvironmentRoot $runtime
& $python -m meeting_intelligence.web --environment-root $runtime --port 8001
```

Open http://127.0.0.1:8001. Compiled Tailwind CSS is included; `npm run build:css` rebuilds it after styling changes. The smoke test checks imports, audio decoding, a local FastAPI request and metric calculations; it does not verify credentials or model access.

### Use and recovery

Upload a recording, optionally specify its actual meeting date and an excerpt interval, and select speaker identification. The app saves each completed stage under `$runtime\outputs\web\<meeting-id>`. A failed or interrupted job can retry its unfinished stages. JSON download can contain partial results if the job failed. Ask self-contained questions; the app does not maintain conversational follow-up memory.

Audio and generated files stay in the runtime directory. Transcript text is sent to Gemini. The app is a local single-user service without login; bind it to loopback as shown. Keep one server process per runtime directory.

Gemini quota belongs to the Google project and may be shared with other clients. The validation scripts use a persistent cap of 20 attempted calls, cache successes and avoid automatic retries; this cap is not a guarantee of available account quota. The ordinary web app does not use that validation ledger. Do not run the final validation API stages and the budgeted demo server concurrently, because they share a single ledger.

For reproducible evaluation, read the evidence JSON under `evaluation` and the historical documentation in the preserved revision linked below. Historical scores use preserved outputs and frozen source hashes. A current-code rerun is a new experiment and must not replace the baseline.

Historical evaluation scripts require their matching frozen source or archived evaluation bundle, including its original protocol documents. They should not be run as a new experiment from this documentation-only checkout. [Preserved documentation and protocol](https://github.com/sharanjaikumar11/ai-meeting-intelligence/tree/1aa610bbf3363f2b398ebbcca90b99d79f940492/docs).
