# Day 7 web application

The FastAPI backend and HTML/Tailwind/CSS/JavaScript interface connect recording upload, local Whisper transcription and speaker diarization, Gemini summaries, action extraction, decision histories, and evidence-backed questions. This is a single-user local application, not an authenticated public service.

## Start

From the source repository:

```powershell
$root = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$root\.venv\Scripts\python.exe" -m meeting_intelligence.web --environment-root $root --port 8001
```

Open `http://127.0.0.1:8001`. The configured `.env` stays on the server. The browser receives no API keys. The existing runtime includes FastAPI, Uvicorn, multipart support, Whisper and Gemini dependencies.

Upload an audio/video recording (maximum 500 MB), optionally specify its date and an excerpt interval, then choose whether to identify speakers. Audio stays local. Transcript text goes to Gemini for analysis and each question. Full-recording processing can be slow on the CPU; try a short excerpt first. The transcript size limit from the earlier modules still applies.

The interface provides Overview, Action items, Decisions, Transcript, and Ask the meeting sections. Evidence expands to exact transcript quotes, timestamps and available speaker IDs. Unknown owners/dates remain explicit. Ask self-contained questions; conversational follow-up memory is not implemented. JSON download combines all currently completed stages; it can be partial if processing failed.

## Persistence and recovery

Each upload has a random identifier and its own directory under runtime `outputs/web`. State and results are saved after each stage. A failed or interrupted job can retry unfinished stages without repeating successful work. Only one processing job runs at a time. State-file access is synchronized to prevent Windows readers blocking atomic file replacement. A restart detects interrupted work when the user revisits the job.

The server binds to loopback and validates request hosts and browser origins. File names are display labels, not storage paths. Rendered transcript content uses DOM text nodes. Uploads are retained locally; no retention policy or delete UI is implemented yet. Do not expose this unauthenticated app publicly or run multiple server processes against the same data directory.

## Frontend build and tests

Compiled CSS is included, so running the app requires no browser CDN. To rebuild:

```powershell
npm ci
npm run build:css
```

Tailwind and Playwright versions are pinned in `package-lock.json`. `node scripts/verify_web_ui.mjs` checks the running app on port 8001 at desktop and mobile sizes. Its section/QA content is explicitly mocked; its screenshots are saved under `.cache/day07-browser`. This is separate from real-model verification.

The API integration tests cover uploads, persisted results, downloads, failures and retries, cross-origin/host rejection, validation and all four processing stages. They mock model calls rather than treating a fake response as a live result. On this Windows environment, tests need permission for asyncio's local socketpair initialization outside the filesystem sandbox.

`scripts/verify_day07_live.py --environment-root ROOT` uploads the public AMI MP4 fixture to the running local API, waits for the real models, downloads combined JSON, and asks one live question. Results are saved at runtime `outputs/day07/live_validation.json`.

## Verification status

Completed 2026-11-17. **114 automated tests passed.** Desktop/mobile browser checks passed and screenshots were inspected. A real public AMI MP4 upload completed all stages with Whisper Small, local pyannote diarization, and Gemini 2.5 Flash: 12 transcript segments, three estimated speaker labels, a summary, one extracted action, and no agreed decisions in this introductory excerpt. The JSON download matched saved results. Live QA correctly identified the remote-control design purpose and design brief, with four exact evidence references.

The live meeting ID is `8a118679c2cf44f281c97e10bfe47d1a`; report: runtime `outputs/day07/live_validation.json`. This is an actual model run, separate from mocked API/browser tests. The MP4 itself is a generated format-test clip containing public AMI audio, not an original camera recording. Scope is the full uploaded 60-second clip, not the entire original meeting. Short recordings can still under-separate speakers; these integration checks are not an accuracy benchmark.

The previous Day 6 decision-question check also passed, correctly distinguishing the agreed JSON format from unresolved hosting. Both daily checkboxes are now complete. Broader recording coverage, hallucination testing and formal quality metrics remain Days 8–9.
