# Day 4: Action items, responsible persons, deadlines, and pending questions

Functional implementation completed 2026-11-15 using Gemini 2.5 Flash. Decision changes and final agreed decisions remain Day 5 work.

## Implementation

`meeting_intelligence.extract_actions` accepts the existing transcript JSON and writes `actions.json` and a readable `actions.txt`. It uses a separate structured response schema and prompt; Day 3 summary behavior remains available independently. Existing output files are not overwritten.

Each action contains its task, assignment type (assignment, commitment, or suggestion), owner, deadline, and supporting segment references. The application copies quotes, timestamps, and speaker IDs directly from the source transcript and checks the transcript fingerprint. This verifies provenance, not whether the model interpreted the conversation correctly.

Named owners require an exact supported name. Roles and groups remain roles/groups rather than invented person names. First-person commitments use a speaker ID when the cited speech establishes one; a person's name requires an explicit user-confirmed speaker mapping. Missing owners remain null.

Deadline text is retained verbatim. Full ISO dates can be normalized; today, tomorrow, the day after tomorrow, and supported `in N days` expressions require an explicit meeting date. The system never substitutes today's date. Weekdays, partial dates, times, and event-relative expressions remain unresolved instead of guessing a calendar date. Each normalized date retains its source phrase and resolution explanation.

Pending questions are scoped to the supplied transcript. An excerpt cannot establish whether a question was answered later in the full meeting. Suggested actions are distinguished from informational questions. No current task completion status is inferred.

## Usage

Run from the source repository after configuring GEMINI_API_KEY in the runtime directory's `.env`:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence.extract_actions `
  "$envRoot\outputs\day04\assignment_excerpt\transcript.json" `
  --environment-root $envRoot --output "$envRoot\outputs\new-actions"
```

Add `--meeting-date YYYY-MM-DD` only when the meeting date is known. The existing input size limit applies; long-meeting chunking is not implemented.

## Verification and observed limitations

- Regression suite: **62 tests passed**, including 26 Day 4 cases covering owner resolution, date handling, missing fields, invalid evidence, pending questions, empty transcripts, and CLI/schema integration.
- Real input: Whisper Small transcription of AMI ES2002a, seconds 970–1100. This development excerpt was transcribed without diarization; roles came from spoken text, not speaker identity.
- Live real output: `outputs/day04/ami_actions_v2/actions.json` contains four extracted items and no pending questions. Review found three role assignments plus **one false positive**: receiving emailed instructions was treated as an assigned task. The user-interface role wording is incomplete in the ASR transcript and remains incomplete in the output. Event-relative deadlines remain unnormalized. All 13 evidence references match the source transcript.
- Live synthetic output: `outputs/day04/synthetic_actions_v2/actions.json` contains five actions and one pending hosting-region question. Alice's tomorrow deadline resolves to 2026-04-02 from the explicitly supplied fixture date 2026-04-01; Bob's date remains 2026-04-06. The checklist owner and first-person speaker identity remain unknown. Dashboard review is a suggestion, with `next Friday` unnormalized. The answered CSV/JSON question is excluded. All 13 evidence references match the fixture.
- The synthetic transcript is authored text in `tests/fixtures/day04_synthetic_transcript.json`, not recorded speech or held-out evaluation data. Earlier live runs are retained in `ami_actions` and `synthetic_actions`; v2 addressed missed elliptical assignments and suggested-action classification but still has the real false positive noted above.

Recheck provenance with `scripts/verify_day04.py TRANSCRIPT.json ACTIONS.json`. The verifier checks schema, fingerprint, and exact evidence fields; it does not score semantic correctness. Precision, recall, and F1 will be measured on labeled evaluation data in Day 9. These development checks do not establish general extraction accuracy.

## Follow-up fix: passive notifications (prompt v3)

The v2 false positive above is corrected in the latest verified run. The prompt now explicitly distinguishes predicted events happening to recipients from requested or committed work. It excludes passive notifications without suppressing explicit tasks to send, receive, collect, or review something. No keyword filter or manual deletion of generated items was used.

- `outputs/day04/ami_actions_v3/actions.json`: three genuine role assignments, zero pending questions; the emailed-instructions notification is excluded. All 12 evidence references verified.
- `outputs/day04/notifications_v3/actions.json`: four actions from the new authored fixture `tests/fixtures/day04_notifications_transcript.json`. A calendar-invitation notification and automatic server restart are excluded; explicit emailing, sending, receiving equipment, and reviewing notes remain. All 10 evidence references verified.
- `outputs/day04/synthetic_actions_v3/actions.json`: the original five actions and one hosting-region question remain, with the expected owners, dates, and suggestion classification. All 13 evidence references verified.
- The complete existing regression suite passed again: **62 tests**. The three live model checks above are separate from the offline tests and actually exercise the revised prompt.

The earlier v2 files remain as diagnostic history. V3 is the current prompt/output reference. This fixes the observed case in the tested runs; it does not guarantee every future model response is correct. Incomplete ASR role wording and ambiguous event-relative deadlines remain as documented.
