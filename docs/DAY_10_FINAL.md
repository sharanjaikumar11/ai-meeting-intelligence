# Day 10 validation and publication

## Unseen action extraction: 2026-11-23

The frozen candidate was evaluated on 20 reference tasks in six project-unseen AMI excerpts (553 seconds). References were annotated by the assistant from AMI human transcripts before prediction. This is a small, purposively selected kickoff-meeting sample, not an official test split or independent human validation. Whisper small used beam size 5; the ordinary web app retains its existing decoding default.

| Metric | Result |
|---|---:|
| Task-intent precision | 91.67% (11/12) |
| Task-intent recall | 55.00% (11/20) |
| Task-intent F1 | 68.75% |
| Word error rate | 21.44% (300/1,399 words) |
| Correct owners among matched tasks | 8/11 |
| Complete/correct details among matched tasks | 8/11 |

There were 11 true positives, one false positive and nine false negatives. The 85–90% recall target was **not achieved**. The previous 80% recall was a development result on five already-known tasks; it is not comparable to this new sample as evidence of improvement or regression.

The TS3006a extraction failed owner-evidence validation after its single correction attempt. No action output was delivered, so all four reference tasks count as false negatives. The failed case remains in the denominator. Its invalid candidates are retained in the private runtime validation cache, with their hashes recorded in the review ledger.

Other omissions include all three ES2006a assignments despite their presence in the transcript, and ES2010a's technical-functions assignment. ES2011a's extracted instruction to find out what technical functions means was judged a clarification, not the assigned design deliverable, and counted as a false positive. Unknown/misassigned roles and omitted task details remain separate errors rather than being hidden by task-intent matching.

There are no positive task deadlines in this sample, so it does not estimate deadline accuracy. No decision or QA aggregate was recomputed on these six excerpts. The frozen Day 9 metrics remain the baseline for those categories.

## Follow-up checks on known errors

The recovered 30-second IS1003b audio produced correct separate QA claims for the Industrial Designer's components work and the User Interface Designer's interface concept. Action extraction nevertheless still omitted the components task and produced a vague additional task; recovered speech is not equivalent to recovered action recall.

The recommendation owner is now retained as the explicitly stated group `we`. Its task description remains generic. The budget QA follow-up correctly reports removal of voice recognition and avoids calling the disputed 12.25/12.50 value final. These are targeted development checks, not a new six-question QA benchmark.

The teletext outcome remains ambiguous in both the human annotation and original ASR around IS1003b.sync.392. No independent listening adjudication was obtained. Keep the frozen decision reference and its uncertainty; do not count this as a definitively resolved model error.

## Reproducibility

Gold, semantic review and metrics are in `evaluation/day10_unseen_gold.json`, `evaluation/day10_unseen_review.json` and `evaluation/day10_unseen_metrics.json`. Scoring checks the frozen candidate, artifact hashes, every case, one-to-one semantic matches, exact evidence and recomputed WER. Windows text reads explicitly use UTF-8 to preserve currency symbols during scoring.

From the source checkout with the original runtime artifacts:

```powershell
$runtime = 'C:\Users\shara\Projects\ai-meeting-intelligence'
& "$runtime\.venv\Scripts\python.exe" scripts/score_final_validation.py --environment-root $runtime
```

Runtime evidence is under `outputs/day10/final_2026-11-23`. Raw recordings and full runtime outputs are excluded from Git. Original downloads failed; a pinned third-party AMI mirror was used, with LFS SHA-256 checks and a control recording matching an existing official download. Exact source URLs, revision and reference hashes are retained in runtime `provenance.json`.

## Release checks

Ruff lint, Ruff formatting, ESLint and 176 regression tests passed. The installed-environment smoke check passed dependency imports, FFmpeg/Whisper preprocessing, TorchCodec decoding, a local FastAPI request and metric calculations. Desktop/mobile UI checks passed; their section and QA fixtures are explicitly mocked and do not establish model accuracy.

The fresh 60-second public AMI MP4 upload completed all four stages: transcript/speaker labeling, summary, actions and decision tracking. JSON download exactly matched the saved combined result, and its transcript references were verified. Meeting ID: `d6992b7818a74fe7b64002f52cf7d0a2`; evidence: runtime `demo.json` and `demo.result.json`. This is a format-test video carrying public AMI audio, not an original camera recording or a full-length meeting.

Fresh demo QA was deliberately not run: after the upload pipeline the remaining local request budget cannot fund both a new answer and its mandatory review. The historical Day 7 real-model demonstration covered upload, all processing stages, JSON download and live QA. The two targeted Day 10 QA checks described above were also live, but are distinct from this new upload. Do not report a complete fresh end-to-end QA revalidation.

The public repository is https://github.com/sharanjaikumar11/ai-meeting-intelligence. Publication does not mean all accuracy limitations are solved. Remaining work is the fresh demo QA rerun with quota, independent teletext adjudication, higher task recall and owner/detail accuracy, and independent reference review.
