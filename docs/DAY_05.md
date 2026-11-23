# Day 5: Decision and deadline tracking

Functional implementation verified 2026-11-16 with Gemini 2.5 Flash. This completes the Day 5 module; interactive QA and UI integration remain Days 6 and 7.

## Behavior

Update 2026-11-16: the latest version adds source-grounded review and `recalled` historical events. Real recordings now supplement synthetic checks for design and deadline changes. See [quality follow-up](DAYS_01_05_QUALITY_REVIEW.md); earlier v2 findings below are preserved as development history.

`meeting_intelligence.track_decisions` reads a Day 2 transcript and writes `decisions.json` and `decisions.txt` into a new directory. It works independently of Day 4 output and does not alter it. Each topic is a distinct decision or task deadline, with a chronological list of proposed, agreed, disagreed, reopened, deferred, and withdrawn events.

Every event retains exact transcript quotes, timestamps, and available speaker IDs. The event anchor identifies where the event happens; supporting context can include earlier proposal segments. Local validation checks anchors, chronology, exact deadline phrases, and references to earlier unresolved events. The model cannot directly set the final state: application code derives it from the validated events.

- Accepted replacements retain prior agreement history; direct replacements link to the superseded active agreement.
- Proposed revisions remain visible without replacing an existing agreement.
- Disagreements remain in the history after resolution. Explicit resolution links close earlier issues.
- Unresolved objections, reopened discussions, or deferred issues prevent a claim of a final agreed outcome. The last historical agreement remains separately available.
- Withdrawal removes the active agreement. Topics with no agreement remain unresolved.
- Deadline normalization reuses Day 4 rules: explicit ISO dates and supported relative dates with a supplied meeting date. Ambiguous dates remain unresolved; current time is never substituted.
- Assignments, predictions, existing constraints, and meeting schedules are not automatically treated as agreed decisions or task deadlines.

“Final” always means within the supplied transcript interval. No cross-meeting identity matching or current real-world task status is inferred. The JSON includes input scope, processed interval, source fingerprint, model/prompt version, and limitations.

## Run

From the source repository, with the configured runtime `.env`:

```powershell
$envRoot = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$envRoot\.venv\Scripts\python.exe" -m meeting_intelligence.track_decisions `
  "$envRoot\outputs\day04\assignment_excerpt\transcript.json" `
  --environment-root $envRoot --output "$envRoot\outputs\new-decisions"
```

Add `--meeting-date YYYY-MM-DD` only for the actual known meeting date. Existing output directories are preserved. An empty transcript returns an empty result without an API request. Invalid responses trigger at most one model correction; a second invalid response fails without saving output. Network failures are not treated as structural corrections. Correction warnings are retained in successful outputs. Usage metadata currently describes the final response, not total retry cost.

## Verification

The complete regression suite passed: **81 tests**, including 19 Day 5 cases. Coverage includes accepted replacements, unaccepted proposals, reopened/deferred discussions, objections and their explicit resolution, deadline normalization, withdrawal, independent topics, invalid chronology/references, exact deadline evidence, empty input, output preservation, and bounded correction behavior.

Live verification used two development inputs:

| Input | Verified outcome | Evidence references |
| --- | --- | --- |
| Authored synthetic transcript | Three topics: CSV changed to JSON after resolving an objection; deadline changed from April 6 to April 8, with a later April 10 suggestion left unaccepted; hosting disagreement remains unresolved | 13 |
| AMI ES2002a, seconds 970–1100, Whisper Small transcript | One unresolved remote-control feature-scope topic; no invented final agreement, emailed-instructions decision, or meeting-time task deadline | 7 |

Saved outputs are under the runtime directory:

- `outputs/day05/synthetic_v2/decisions.json` and `decisions.txt`
- `outputs/day05/ami_v2/decisions.json` and `decisions.txt`

Both successful live runs used the single permitted correction. All evidence fields and transcript fingerprints were verified. The synthetic outcome assertions also checked final deadline, decision, historical agreement, proposed revision, and unresolved disagreement.

Reproduce saved-result checks:

```powershell
& "$envRoot\.venv\Scripts\python.exe" scripts/verify_day05.py `
  tests/fixtures/day05_synthetic_transcript.json `
  "$envRoot\outputs\day05\synthetic_v2\decisions.json" --synthetic-expectations
& "$envRoot\.venv\Scripts\python.exe" scripts/verify_day05.py `
  "$envRoot\outputs\day04\assignment_excerpt\transcript.json" `
  "$envRoot\outputs\day05\ami_v2\decisions.json"
```

## Limits and development findings

Initial live responses confused issue-resolution references with superseded agreements. They were rejected by local validation. The first saved real candidate (`ami_v1`) also overclassified assignments and predictions as agreements. The current v2 prompt clarifies those distinctions; earlier output is retained as diagnostic history and is not the recommended result.

The real excerpt does not contain an explicit accepted decision/deadline change, so change handling was verified with authored text, not real audio. The synthetic fixture is explicitly labeled and is not held-out evaluation data. The real output's “deferred” label summarizes the absence of a settled choice and the statement that the choice is up to the team; it does not establish a scheduled follow-up or explicit consensus to defer.

Provenance and state consistency checks cannot establish semantic accuracy. ASR errors, imperfect topic grouping, missing context, and model classification errors can still affect output. Inputs retain the existing 120,000-character limit; long-meeting chunking is not implemented. Formal decision precision, recall, and F1 remain Day 9 work.
