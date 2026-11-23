# Public GitHub publication review

Reviewed on 2026-11-23. Public repository created with explicit user authorization: https://github.com/sharanjaikumar11/ai-meeting-intelligence. This document records the reviewed publication scope; Git history records the eventual commit and push.

## Commit contents

| Contents | Include | Purpose |
|---|---|---|
| `meeting_intelligence/*.py` | Yes | Transcription, speaker alignment, summaries, actions, decision tracking, QA and FastAPI application |
| `meeting_intelligence/static/` | Yes | HTML, JavaScript, styles and compiled Tailwind CSS needed to run the UI |
| `tests/` | Yes | Regression tests and explicitly synthetic transcript fixtures |
| `scripts/` | Yes, after final review | Dataset preparation, validation, scoring, UI checks and repeatable pre-commit checks; distinguish experimental helpers from completed verification |
| `evaluation/` | Yes | Public-AMI reference labels, adjudication, measured metrics and known limitations; no invented final scores |
| `docs/` and `README.md` | Yes | Setup, daily results, evaluation methods, limitations and this review |
| `data/README.md`, `data/manifest.csv`, `data/provenance.json` | Yes | Public dataset attribution, selected-recording metadata and provenance; no recordings |
| `requirements.in`, `requirements.lock.txt`, `requirements-dev.txt` | Yes | Python dependency specifications and tested version pins |
| `package.json`, `package-lock.json` | Yes | Reproducible frontend build and lint dependencies |
| `pyproject.toml`, `eslint.config.mjs` | Yes | Ruff and JavaScript lint configuration |
| `environment_smoke_test.py` | Yes | Installed-dependency and decoder verification |
| `.gitignore`, `.env.example` | Yes | Runtime exclusions and empty credential template |

## Excluded contents

Do not publish `.env` or real credentials, `.venv`, `node_modules`, Python bytecode, `.cache`, `.pytest_cache`, `.ruff_cache`, logs, downloaded model weights, FFmpeg binaries, dataset archives, raw recordings, full downloaded references, or runtime `outputs`. The runtime lives separately at `C:\Users\shara\Projects\ai-meeting-intelligence`; it is not the source repository.

The included evaluation references concern the public AMI corpus, and test fixtures are synthetic. Existing historical reports retain local filesystem paths for provenance and reproducibility. They do not contain credentials. The application has no separate user-supplied private meeting dataset in the candidate file list.

## Checks and release status

Ruff lint, Ruff formatting, JavaScript ESLint and all 176 regression tests passed before this review. The dependency smoke check also passed imports, FFmpeg/Whisper preprocessing, TorchCodec decoding, a local FastAPI request and metric calculations. A credential-pattern scan of candidate source files found no matches; this is a bounded scan, not a guarantee that arbitrary secrets cannot exist.

The final unseen evaluation is scored, including TS3006a's owner-evidence validation failure: recall is 55% across all 20 tasks. The scorer was executed successfully. See `DAY_10_FINAL.md` for measured results and fresh-demo status. Do not present the recall target as achieved or imply that publication resolves the remaining accuracy issues.

Before publication, finish or explicitly document these remaining checks, rerun `scripts/check.ps1`, review the exact staged diff and credential exclusions, and then commit and push. Public repository creation is authorized by the user. No additional approval is required for that requested publication, but the documentation must accurately describe the state being published.
