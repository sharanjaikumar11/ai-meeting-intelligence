# Day 6 interactive meeting questions

The Python module `meeting_intelligence.qa` provides a terminal conversation loop and single-question JSON export. The web UI and combined application pipeline remain Day 7 work.

Run from the source repository:

```powershell
$root = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$root\.venv\Scripts\python.exe" -m meeting_intelligence.qa `
  "$root\outputs\day02\speaker_context\transcript.json" --environment-root $root
```

Ask a self-contained question at each prompt; `/exit` ends the session. Questions are independent, not chat-history follow-ups. Add `--question "What decisions were made?" --output "$root\outputs\my-answer.json"` for one saved answer. Existing files are preserved. The transcript stays in memory for an interactive session; each question sends the full supported transcript interval to Gemini. Empty transcripts require no API call.

The answer contains status (`answered`, `partial`, `not_found`), claims, exact source quotes/timestamps/speaker IDs, limitations, source fingerprint, scope, model metadata and usage. Missing information triggers abstention or a partial response. Assigned tasks do not establish present-day pending status. Tentative deadlines stay tentative; ambiguous dates are not converted using today's date. Named people require explicit evidence.

The CLI uses Gemini extraction followed by a transcript-grounded review. The application then validates schema and segment IDs and copies evidence directly from the transcript. This prevents fabricated citation text, but does not prove semantic correctness. Both calls' token usage is recorded. API failures or invalid outputs are not saved as answers; interactive users can ask another question after a recoverable failure.

Full-context QA is used rather than a vector index so later changes are available to the model. The existing 120,000-character transcript limit applies; oversized inputs fail explicitly. Long-meeting chunking, conversational memory and web chat are not implemented. ASR errors and uncertain speaker labels can still affect answers.

## Development verification

Offline tests cover evidence copying, invented IDs/quotes, invalid questions, partial answers, abstention, empty speech, interactive exit, output preservation, and review usage. Live checks use authored fixtures and the public AMI EN2002d excerpt, not private recordings or held-out evaluation data.

Saved under runtime `outputs/day06`:

- `deadline.json`: April 8 remains agreed; April 10 is an unaccepted suggestion.
- `tasks.json`: Alice's report and Bob's README assignments; present-day status correctly marked unknown.
- `missing.json`: revenue question correctly receives no invented answer.
- `real_deadline.json`: initial diagnostic answer retained for comparison; it repeated a garbled ASR phrase.
- `real_deadline_reviewed.json`: review-enabled real-recording answer.
- `decisions_reviewed.json`: completed 2026-11-17. Correctly answers JSON for the export format and explains that hosting remains deferred. The partial status preserves the absence of an agreed hosting choice. Fingerprint and cited evidence passed verification.

Status: Day 6 complete as of 2026-11-17. The quota-blocked check has now passed. Five accepted live answers passed source-fingerprint and evidence checks (the initial three fixture checks used one generation call; the real-recording and final decision checks used extraction plus review). These development checks do not establish accuracy on every question or meeting.

Use `scripts/verify_day06.py TRANSCRIPT.json ANSWER.json` to verify saved answer provenance. Formal QA correctness evaluation remains Day 9; these few development checks are not a general accuracy score.
