# Day 8: varied recordings, edge cases and hallucination checks

## Dataset and scope

Three additional public English meetings were downloaded sequentially from the [official AMI distribution](https://groups.inf.ed.ac.uk/ami/download/), with the corpus human annotations used for review. Attribution: AMI Consortium / University of Edinburgh, CC BY 4.0. Full recordings, SHA-256 hashes and URLs are retained in runtime `data/day08/provenance.json`. No credentials are stored in reports.

| Meeting | Full download | Processing scope | Purpose |
| --- | --- | --- | --- |
| ES2005a | 477.88 seconds | Whole recording | Research assignments, ambiguous owners and missing dates |
| IS1001b | 2116.69 seconds | 1700–2090 seconds | LCD/speech-recognition choices and follow-up work |
| TS3005d | 2672.20 seconds | 1500–1810 seconds | Cost-driven design changes, objections and final feature choices |

All three test intervals have four speakers in the human reference. Speaker identities in model output remain estimates; matching the speaker count does not establish diarization accuracy. The two longer meetings are excerpt tests, not claims of full-meeting evaluation. These meetings are now development/error-analysis data and must not be reported as an untouched Day 9 test set.

The existing full ES2002d web job was stopped with the user's approval after roughly 49 minutes of processing. Its recording and saved files were preserved; it is not counted as a successful Day 8 run.

## Checks

- Run real Whisper Small, local pyannote Community-1 and Gemini 2.5 Flash through the web pipeline.
- Validate transcript schema, time bounds, source fingerprints and every emitted evidence quote, timestamp and speaker ID.
- Check the downloaded JSON equals the saved pipeline output.
- Compare substantive assignments and decisions with AMI human reference turns, retaining uncertainty about omitted context.
- Ask a supported question and an unrelated bank-account question for each AMI case; require abstention for unsupported information.
- Test digital silence, a damaged file, a video without audio, and an offset past the end.
- Compare a clean 70-second ES2005a section (170–240 seconds) with the same signal plus deterministic 5 dB SNR noise. The noisy copy is explicitly artificial, not a naturally noisy AMI recording.
- Use a separate authored text fixture to test rejected deadline changes, missing ownership, deferred choices and quoted prompt injection. This is not recorded meeting evidence.

## Issues found and changes

1. Whitespace-only questions reached the QA handler and surfaced as a server error. Input now strips surrounding whitespace before validating length and rejects blank questions with HTTP 422.
2. Damaged media, video without audio and out-of-range offsets previously shared a generic processing error. A dedicated safe input-error type now exposes the actionable reason while unexpected exceptions remain sanitized.
3. In the first live authored-fixture run, a Friday deadline was explicitly reaffirmed after rejecting Monday, but the rejection remained an unresolved event. The decision extraction and review instructions now require the reaffirmation to resolve the settled proposal and rejection, including events from the same turn. Genuine unresolved objections still block final agreement. A reducer regression verifies this chronology.
4. The same fixture produced the action description `author is Alex.` rather than identifying the work. The action prompt now requires a clear verb and work object, while retaining exact source phrases for owners/deadlines.

Original and corrected live results are kept separately, not overwritten. Prompt versions are `day08-actions-v4` and `day08-decisions-v6`.

5. Whisper transcribed the word `you` from a 20-second digital-silence fixture. The pipeline now checks decoded PCM and bypasses both models only when every sample is exactly zero. It returns empty speech, explicit skipped-model metadata, and no extracted content. Both the direct pipeline and real web upload passed after the fix. One nonzero sample prevents this shortcut; quiet speech is retained.
6. The artificial 5 dB noise copy substantially corrupted the words. An uncertainty warning now flags recordings with at least 10 scored words where at least 20% have Whisper probability below 0.35. This is an uncalibrated review heuristic, not an accuracy score or a denoising fix. It flagged the noisy sample (44/122 low-probability words) and did not flag the clean comparison (10/123). Original transcripts are preserved; the saved local report evaluates the new warning separately on those existing outputs.

## Reproduce

From the source repository, using the configured runtime environment:

```powershell
$root = 'C:\Users\shara\Projects\ai-meeting-intelligence'
$python = "$root\.venv\Scripts\python.exe"
& $python scripts\prepare_day08.py --environment-root $root
# Start the app in another terminal; see DAY_07.md.
& $python scripts\verify_day08_live.py --environment-root $root
& $python scripts\verify_day08_edges.py --environment-root $root
& $python scripts\verify_day08_adversarial.py --environment-root $root --label adversarial_corrected
# Local-only checks (no Gemini calls; reuses completed audio outputs):
& $python scripts\verify_day08_local.py --environment-root $root
$env:MEETING_ENV_ROOT = $root
& $python -m pytest tests -q
```

The real-model scripts save resumable results under runtime `outputs/day08`. They do not silently retry failed jobs or bypass API quotas. Provenance/evidence checks verify the source of a claim, not whether its meaning is correct; semantic review and formal Day 9 metrics are separate.

## Verification status

Local checks completed 2026-11-19. **129 automated tests passed in the final run.** A background-job test initially exceeded its short polling budget during Windows I/O; its bounded wait was increased before the final passing run.

| Real recording test | Segments | Predicted / reference speakers | Overlap-flagged segments | Result |
| --- | ---: | --- | ---: | --- |
| ES2005a whole recording | 87 | 4 / 4 | 44 | Transcription and timeline validation passed; Gemini summary blocked |
| IS1001b excerpt | 133 | 3 / 4 | 70 | Transcription passed; speaker under-separation remains; Gemini summary blocked |
| TS3005d excerpt | 177 | 4 / 4 | 127 | Transcription and timeline validation passed; Gemini summary blocked |
| ES2005a clean 70-second copy | 17 | 2 predicted | 5 | Completed; short-clip speaker separation and word errors remain |
| Same copy plus 5 dB noise | 17 | 2 predicted | 6 | Completed technically, but substantial transcription corruption; review warning triggered |

These counts are diagnostics, not WER, diarization accuracy, or extraction F1. Manual comparison against AMI reference turns confirmed that the IS1001b transcript preserves the no-LCD/no-speech decisions around 1945–1952 seconds, and TS3005d preserves restoring the curve and dropping speech recognition/scroll wheel around 1774–1799 seconds. ES2005a preserves the broad research assignments around 180–230 seconds but contains errors such as `low controls` for remote controls. Speaker boundaries sometimes split a single utterance incorrectly even when total speaker count is four. ES2005a human word annotations end near 306 seconds while the audio continues to 477.88 seconds; later transcript text is not validated against those annotations and is not assumed to be hallucinated merely because annotation is absent.

The silence upload returned no transcript segments, summary statements, actions or decisions. Corrupt media, video without audio, and offsets after the end failed with the expected actionable error messages. All four real API edge cases passed. Saved evidence is under runtime `outputs/day08/local_checks.json` and `edge_reports.json`; original and corrected silence transcripts are retained separately.

The initial live authored fixture correctly kept unknown ownership and declined launch approval; however its decision timeline incorrectly remained unresolved after reaffirmation. The corrected live action output is now `Write the report`, assigned to Alex with Friday retained without an invented calendar date. On the subsequent user-authorized retry, the corrected decision and QA run also passed: Friday is agreed with no remaining deadline objections, hosting is unresolved, accessibility ownership remains unknown, and launch approval is denied. All 35 evidence references in the corrected fixture were verified. The original failed fixture remains preserved.

## Pending Gemini checks — explicitly deferred by the user

On 2026-11-18 Gemini reported exhausted daily quota. The user chose to finish local checks and leave Gemini checks pending. No Gemini requests were made during that local-only continuation. The user subsequently requested a fresh Gemini check: access worked, the corrected authored fixture completed, and AMI analysis resumed, but daily quota was exhausted again. Day 8 remains unchecked overall.

- Resume the three AMI web jobs from their saved transcripts; run summaries, actions and decisions, then review substantive output against the human reference turns.
- Run the supported and unanswerable questions for all three recordings; validate evidence and semantic correctness.
- Recheck ES2005a action ownership and speaker-to-task QA after the new pronoun/ownership guards. The corrected authored decision/QA fixture is now complete.
- Test downstream extraction on the noisy transcript if evaluating the complete degraded-audio pipeline. Its local transcription result alone is not an extraction-quality pass.

After quota is available, start the updated app, then explicitly resume using:

```powershell
& $python scripts\verify_day08_live.py --environment-root $root --retry-failed
& $python scripts\verify_day08_adversarial.py --environment-root $root --label adversarial_corrected
```

The saved AMI transcripts are reused, avoiding another transcription run. Genuine noisy/overlapping-speech errors, speaker under-separation, and hallucinations in non-silent signals remain possible. Formal WER, extraction F1 and QA correctness belong to Day 9 and are not claimed here.

## Latest Gemini retry results

| Case | Saved progress | Review outcome |
| --- | --- | --- |
| Authored corrected fixture | Summary, actions, decisions, QA complete | Friday reaffirmation, unknown ownership and no launch approval verified; 35 source references checked |
| ES2005a | All extraction stages and both QA calls complete | 85 extraction evidence references verified, plus QA references; unanswerable bank-account question correctly abstained. Semantic issues remain, so this is not a complete accuracy pass |
| IS1001b | Transcript, summary and actions saved | Summary correctly excludes LCD and speech recognition. Daily quota blocked decision tracking; QA not run |
| TS3005d | Transcript saved | Daily quota blocked summary; later extraction and QA not run |

Three initial AMI summary attempts failed local schema validation. The summary prompt now explicitly states its length/evidence limits, and each draft/review permits at most one schema correction, preserving evidence and counting usage. ES2005a and IS1001b summaries subsequently completed. Tests verify correction bounds and usage accounting; malformed content is never silently accepted.

Semantic review found ES2005a action ownership incorrectly labeling `me` as a person's name. The existing pronoun guard now also rejects object/reflexive pronouns. Its QA answer inferred some speaker-to-task assignments from ambiguous addressees; the QA generation/review instructions now require an explicit task-specific commitment or confirmation and partial status for missing requested information. These two changes pass regression tests, but their real AMI retests are pending quota. **Existing saved ES2005a outputs predate these corrections and must not be presented as corrected results.**

Other observed limits: ES2005a decision output promotes several research assignments into agreed topics, and IS1001b actions include product-design choices as tasks. Those classifications require further review/correction; matching evidence quotes alone does not establish the interpretation. Full Day 8 completion requires closing these remaining semantic checks, not merely obtaining successful API responses.

The final regression suite after this retry contains 135 tests. The batch verifier now stops when daily quota is exhausted rather than retrying every remaining meeting. Saved work is retained for the next authorized retry.
