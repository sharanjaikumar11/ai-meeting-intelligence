# AI Meeting Intelligence Agent

Local Python application for meeting transcription, structured extraction, decision tracking and evidence-backed questions. Public repository: [ai-meeting-intelligence](https://github.com/sharanjaikumar11/ai-meeting-intelligence).

Latest validation (2026-11-23): across six unseen AMI excerpts and 20 reference tasks, task precision is **91.67%**, recall **55.00%**, F1 **68.75%**, and WER **21.44%**. One extraction failed and is included in the score. The 85–90% recall target is not achieved. See [the final validation report](docs/DAY_10_FINAL.md) for owner/detail errors, sampling limits and remaining work.

The v8 development follow-up recovered three known missed assignments in one live check and prevents an invalid owner from discarding every task after correction. **178 tests pass.** This is not a new unseen score; see [the evidence and remaining validation](docs/RECALL_V8.md).

## Run the application

The verified development platform is Windows, Python 3.11 and CPU inference. Run commands from this repository. Keep the runtime directory separate from the source checkout.

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$runtime\.venv\Scripts\python.exe" -m meeting_intelligence.web --environment-root $runtime --port 8001
```

Open http://127.0.0.1:8001, upload audio or video, and start with a short excerpt. The interface shows the transcript, summary, tasks, decision history and evidence-backed answers; Download JSON exports the saved results. CPU processing of full meetings can take substantial time. Speaker labels are anonymous clusters unless a name is supported by the conversation.

For a new machine, see [setup instructions](docs/SETUP.md). The dependency pins describe the tested environment; a clean-machine installation has not yet been independently verified.

## Check before committing

```powershell
npm ci
& scripts/check.ps1 -Python "$runtime\.venv\Scripts\python.exe" -EnvironmentRoot $runtime
```

This runs Ruff lint, Ruff formatting checks, JavaScript ESLint and the Python regression suite. Every check must pass before committing or pushing. Development tools are pinned in `requirements-dev.txt` and `package-lock.json`. Tests use a new project-local temporary directory on each run.

Status: Days 1–9 complete within their documented scope. Day 9's small pilot measured WER 28.27%, action F1 44.44%, final-decision F1 50.00%, and strict QA correctness 4/6. Accuracy needs improvement; these are provisional scores with assistant-authored references, not independent human validation. The local application integrates audio/video upload, timestamped transcription, speaker labeling, summaries, tasks, decision/deadline tracking, evidence-backed questions and JSON download. The latest suite has 176 passing tests. See [Day 9 results and limitations](docs/DAY_09.md). Day 10 remains open.

## Objective

Earlier Day 10 development work: task-intent F1 rose from 44.44% to 88.89% on the same three examples. That was not a held-out score. An initial QA experiment was rejected; later targeted QA checks passed for designer assignments and the voice-recognition decision. The unseen evaluation above supersedes development-only claims about generalization. The regression suite has **176 passing tests**. See [development history](docs/DAY_10_IMPROVEMENTS.md) and [current results](docs/DAY_10_FINAL.md).

Day 8 completed on 2026-11-20 using 20 attempted Gemini calls for the completion run, cached prior work, and local/reference-based verification. Three additional AMI recordings, supported/unsupported questions, silent/invalid input and degraded audio were checked. See [Day 8 results, review methods and accuracy limits](docs/DAY_08.md).

Days 6 and 7 are complete: evidence-backed QA and a local web interface now connect all processing modules. See [QA usage](docs/DAY_06.md) and [web app setup and verified results](docs/DAY_07.md).

Days 1–5 quality follow-up: context-assisted speaker separation, corrected summary claims, and real recorded decision/deadline changes are documented in [the quality review](docs/DAYS_01_05_QUALITY_REVIEW.md). That review recorded 92 passing tests; the Day 7 suite has 114. Historical daily notes retain the original diagnostic results.

Convert audio/video meeting recordings into structured meeting information using Whisper and an LLM, with particular attention to changing decisions.

## Required stack
Python, Whisper, Gemini, FastAPI, HTML, Tailwind CSS, JavaScript. Speaker diarization supplements Whisper for speaker labels.

## Required outputs
- Timestamped transcription with speaker identification.
- Summary, key discussion points, decisions, action items, assigned persons, deadlines, and pending questions.
- Decision and deadline changes, disagreements, unresolved discussions, and final agreed decisions.
- Interactive meeting QA with transcript-based evidence.
- Structured meeting JSON.

## Evaluation
- Speech-to-text: WER.
- Action items: precision, recall, F1.
- Decisions: precision, recall, F1.
- QA: correctness.

## Final deliverables
1. Working end-to-end Python application.
2. Structured meeting JSON.
3. Interactive QA interface.
4. Evaluation report.
5. GitHub repository with README and verified setup instructions.

See [the daily checklist](docs/PLAN.md), [Whisper notes](docs/DAY_01.md), and [dataset preparation](data/README.md).

The initial model is Whisper `small`. See [measured Day 1 results](docs/DAY_01_RESULTS.md) for the comparison and its limitations.

## Local environment and data

Source code and documentation live in this repository. The isolated environment, models, recordings, and generated outputs live under `C:\Users\shara\Projects\ai-meeting-intelligence`.

Python 3.11, Whisper, pyannote.audio, Gemini SDK, FastAPI, FFmpeg, and evaluation dependencies are installed there. Resolved versions are recorded in that directory's `requirements.lock.txt`. CPU execution is used on the Intel Iris Xe machine.

From this repository in PowerShell:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" scripts/download_ami.py --data-root "$envRoot\data"
& "$envRoot\.venv\Scripts\python.exe" scripts/prepare_ami.py --data-root "$envRoot\data"
& "$envRoot\.venv\Scripts\python.exe" scripts/benchmark_whisper.py --environment-root $envRoot --models tiny base small --threads 4
```

The download script obtains three public AMI English meetings sequentially. Preparation converts corpus manual annotations into JSON/text references and freezes three development-only clips. Benchmarking saves predictions, timestamps, WER counts, and CPU timing under `outputs/day01` in the environment directory. It does not use the held-out meeting for model selection.

These commands prepare and benchmark the dataset; they do not launch the future meeting application. Gemini and diarization model credentials are not required for Day 1.

## Day 2 transcription

See [Day 2 usage and model access](docs/DAY_02.md). From this source repository:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence `
  "$envRoot\data\recordings\ES2002a.Mix-Headset.wav" `
  --environment-root $envRoot --output "$envRoot\outputs\my-transcript" `
  --start 60 --duration 120
```

This example uses the configured HF_TOKEN and model access to obtain speaker-labelled transcripts. Add `--skip-diarization` only for an explicitly unlabelled result. Choose a new output directory for each run. The token is stored locally in the environment directory's ignored `.env` file.

## Day 3 summaries and discussion points

Set GEMINI_API_KEY in the environment directory's `.env`, then run from this repository:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence.summarize `
  "$envRoot\outputs\day02\speaker_demo\transcript.json" `
  --environment-root $envRoot --output "$envRoot\outputs\day03\speaker_excerpt_summary"
```

The example summarizes a two-minute excerpt using Gemini 2.5 Flash and exports JSON/text with supporting transcript quotes and timestamps. See [Day 3 configuration, live validation, and limitations](docs/DAY_03.md).

## Day 4 action items, owners, and deadlines

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence.extract_actions `
  "$envRoot\outputs\day02\speaker_demo\transcript.json" `
  --environment-root $envRoot --output "$envRoot\outputs\my-actions"
```

Exports `actions.json` and `actions.txt`, including pending questions and timestamped evidence. Optionally supply `--meeting-date YYYY-MM-DD` using the recording's actual meeting date to resolve supported relative deadlines. Unknown owners and ambiguous dates remain unresolved. See [Day 4 behavior and verification](docs/DAY_04.md).

## Day 5 decision and deadline tracking

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence.track_decisions `
  "$envRoot\outputs\day04\assignment_excerpt\transcript.json" `
  --environment-root $envRoot --output "$envRoot\outputs\my-decisions"
```

Exports `decisions.json` and `decisions.txt`: chronological events, accepted changes, disagreements, unresolved issues, and final agreed outcomes within the supplied transcript. Proposed revisions do not overwrite accepted decisions. Optional `--meeting-date YYYY-MM-DD` supports relative deadline normalization. See [Day 5 design, validation, and limitations](docs/DAY_05.md).

Recall follow-up: an optional beam-search audio recheck recovered missing task evidence, but measured action recall remains 80% pending extraction and unseen-data validation. See [recall diagnostic and 85–90% target](docs/DAY_10_RECALL.md).
