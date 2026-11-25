# AI Meeting Intelligence Pipeline Report

## 1. Project overview

The application converts meeting audio or video into a timestamped transcript, speaker labels and structured meeting information. Whisper Small transcribes the recording locally. Pyannote estimates speaker turns. Gemini 2.5 Flash processes the transcript to produce summaries, actions, decision histories and evidence-backed answers.

The final action-extraction version is v9. On the same 20-task development set, recall improved from 55% to 75% and F1 improved from 68.75% to 81.08%. Precision changed from 91.67% to 88.24%. These are task-extraction results, not speech-recognition accuracy.

## 2. Pipeline workflow

**Meeting audio/video → Input validation → Audio decoding → Whisper transcription → Speaker diarization and alignment → Saved transcript → Gemini extraction → Schema and evidence validation → Structured JSON → Meeting interface and QA**

| Stage | What happens | Output |
|---|---|---|
| Recording input | Accept an audio/video file, optional meeting date and optional excerpt interval | Uploaded recording and processing settings |
| Input validation | Check file size, decodability, available audio and interval bounds | Valid input or an actionable error |
| Audio preparation | FFmpeg decodes the selected audio to 16-kHz mono PCM | Temporary WAV audio |
| Speech recognition | Whisper Small transcribes locally with segment and word timing | Text and original-recording timestamps |
| Speaker diarization | Pyannote estimates speaker turns, including regular and exclusive timelines | Anonymous speaker IDs and turn intervals |
| Alignment | Match timed words/segments to estimated speaker turns | Speaker-labelled transcript |
| Transcript storage | Save the transcript before calling the LLM | Reusable transcript JSON |
| Summary extraction | Gemini drafts and reviews the summary and discussion points | Structured summary with evidence |
| Action extraction | Gemini identifies tasks, owners, deadlines and pending questions | Action JSON with supporting segments |
| Decision tracking | Gemini drafts and reviews chronological decision/deadline events | Topic histories, final state and unresolved issues |
| Validation | Check schema, source IDs, owner/deadline phrases and evidence provenance | Validated results or a controlled failure |
| Results storage | Save each successfully completed stage | Combined meeting JSON and job state |
| Interactive QA | Use the transcript to draft and review an answer to a user question | Answer, supporting evidence and any limitation |

Gemini receives transcript text, not the original recording, in this pipeline. Speech-recognition omissions can therefore cause missing or incorrect downstream information even when the LLM follows its instructions.

## 3. Models and mode of run

| Component | Model or technology | Mode |
|---|---|---|
| Audio/video decoding | FFmpeg | Local |
| Speech to text | Whisper Small | Local CPU |
| Speaker turns | pyannote speaker-diarization-community-1 | Local CPU |
| Summary, actions, decisions and QA | Gemini 2.5 Flash | Hosted API |
| Validation and storage | Python and Pydantic | Local |
| Backend | FastAPI | Local single-user server |
| Interface | HTML, Tailwind CSS and JavaScript | Browser |

Speaker IDs such as `SPEAKER_00` are estimated clusters. They are not proof of a person's name. Named responsibility requires explicit evidence or a user-confirmed speaker mapping.

## 4. Information extracted

| Output group | Information included |
|---|---|
| Transcript | Text, segment IDs, word/segment timestamps, speaker estimates and warnings |
| Summary | Meeting summary and key discussion points |
| Action items | Task, assignment type, owner, deadline and cited evidence |
| Owners | Explicit person, role, group, first-person speaker or unknown |
| Deadlines | Original phrase, resolved date when justified, otherwise unresolved or missing |
| Pending questions | Questions left unanswered in the supplied interval |
| Decisions | Topics, chronological events, current status and final agreed outcome where supported |
| QA | `answered`, `partial` or `not_found`, with claims and transcript evidence |

The combined download has four top-level sections: `transcript`, `summary`, `actions` and `decisions`. QA answers are returned separately by the question endpoint. A failed job may still offer a partial download containing its completed stages.
