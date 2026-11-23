# Days 1–5 quality review

Reviewed 2026-11-16. Work remains within Days 1–5. The original diagnostic outputs are preserved; the newer outputs below supersede them for the specific checks described.

## Speaker separation

The CLI now uses up to 300 seconds of surrounding audio per side when clustering speakers, then crops the turns to the requested transcription interval. Use `--diarization-context 0` for the previous excerpt-only behavior. Surrounding audio increases CPU processing time. Names still require a confirmed mapping; speaker labels alone cannot establish real identities.

For ES2002a seconds 60–180, automatic clustering with context detected four speakers and separated the previously merged introductions. On 255 non-overlapping reference-word midpoints, correctly assigned speakers improved from 245 to 252 (96.08% to 98.82%) after optimal label matching. Three positions remain incorrect/unassigned; 34 overlapping or zero-length reference words were excluded. This diagnostic is not DER or held-out accuracy. Forcing four speakers without context scored only 234/255 and was rejected as the solution.

Evidence: runtime `outputs/day02/speaker_context`, and [machine-readable comparison](verification/speaker_separation.json). `scripts/check_speaker_separation.py` reproduces this check.

## Summary corrections

Summary generation now includes a second source-grounded review of both summary statements and discussion points. Conservative content guards omit the observed corrupt role phrase and duration claims that confuse a next-minutes agenda with total meeting duration. These narrow guards do not guarantee factual correctness for arbitrary claims. Source quotations remain unchanged.

Runtime `outputs/day03/guarded_v5` contains four summary statements and seven discussion points. It correctly describes the planned agenda window and omits the unclear role from generated claims. All 26 evidence references and the transcript fingerprint passed verification with `scripts/verify_summary.py --known-regressions`.

## Real decision and deadline evidence

Two additional public recordings were selected from AMI human annotations as supplementary development cases. They are not held-out evaluation examples; the project's frozen ES2004a test split remains untouched. Download provenance, hashes and human references are under runtime `outputs/day05/real_review_source`. EN2002d audio uses the [official HeadsetAudio mirror](https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/HeadsetAudio/).

- ES2002d seconds 430–630: Whisper Small transcription and live extraction retain the earlier confirmed advanced chip, the proposed removal, and acceptance of a regular chip. `cost_revision_v3` also preserves the double-curved case while retaining an unaccepted single-curve proposal. All 24 references were verified. The earlier broad 450-second candidate exceeded the generation limit and produced no saved decision output.
- EN2002d seconds 1135–1235: real speech recalls a Friday deadline and moves toward trying Monday. `deadline_reviewed_v4` correctly preserves the tentative Monday target and leaves its calendar date unresolved, but omitted the explicit recalled Friday event. The latest v5 schema adds `recalled` events to retain that historical evidence without allowing a later recollection to overwrite a newer agreement.

The current CLI reviews proposed histories against all source turns before local validation. At most one structural correction is allowed. A review uses an additional API call; quota failures save no partial result. Day 5 output applies only to the supplied interval. In particular, a tentative target is not an unconditional commitment and a supplied excerpt cannot prove the full meeting's final outcome.

## Tests and remaining verification

All **92 offline tests passed** after the changes, including context cropping, summary content guards, review evidence checks, quota error redaction, recalled-state preservation, and prevention of historical recalls overwriting newer decisions. Saved synthetic v3 outcomes also passed the original change-tracking checks.

The quota interruption cleared on resumption. `deadline_reviewed_v5` passed provenance checks for all 10 references and retains the recalled Friday date and tentative Monday target. `cost_reviewed_v5` passed all 27 reference checks and retains the accepted advanced-to-regular-chip replacement. Day 5 now allows 16,384 output tokens for longer reviewed histories; truncated responses remain rejected.

Review also exposed a synthetic regression: an objection and reopening in the same turn were collapsed into a single reopened event. The prompt now explicitly requires both events and their resolution links. After one transient 503 failure, the follow-up live run `synthetic_v5_checked` passed all expected outcomes and all 13 evidence-reference checks. The targeted Days 1–5 follow-up verification is complete.

Residual quality limits remain: three scored speaker positions are incorrect/unassigned, ASR wording can be imperfect, and the deadline example contains uncertain earlier recollections and unaccepted alternatives. These are not a claim of perfect recognition or complete semantic accuracy. The verified improvement is separation of the known merged speakers, correction of the two summary claims, and real-audio validation of decision/deadline changes. Broader accuracy metrics remain Day 9 work.

## Reviewed speaker corrections

At the user's request, the three remaining positions were corrected in a separate `outputs/day02/speaker_reviewed` artifact using AMI's human annotations. They cover the missed B vocalization at 151.79–154.48 seconds and D's interjection at 167.36–167.81 seconds. The automatic regular output already detected the D interjection, but exclusive diarization suppressed it. The original automatic output remains unchanged.

The reviewed exclusive timeline scores 255/255 on the same diagnostic, with zero unassigned scored positions. This is supervised correction against the reference, NOT independent evaluation or improved automatic model accuracy. Thirty-four overlapping/zero-length reference words remain excluded; missing ASR words are not invented. The automatic model still scores 252/255. Corrections, reasons and source fingerprint are in `docs/verification/speaker_corrections.json` and alongside the reviewed artifact. The reusable `meeting_intelligence.correct_speakers` command validates and applies explicitly supplied review intervals to a new output directory.
