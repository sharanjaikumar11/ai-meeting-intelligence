# Day 9 evaluation results

Completed **2026-11-22**, within the frozen three-excerpt pilot scope. All required metrics have been calculated from real saved predictions. Evaluation is complete; extraction and answer accuracy still need improvement.

## Results

| Required metric | Result | Counts |
|---|---:|---|
| Speech-to-text WER (lower is better) | **28.27%** | 480 errors / 1,698 reference words |
| Action precision | **50.00%** | 2 TP / 4 predictions |
| Action recall | **40.00%** | 2 TP / 5 reference tasks |
| Action F1 | **44.44%** | 2 TP, 2 FP, 3 FN |
| Final-decision precision | **100.00%** | 1 TP / 1 prediction |
| Final-decision recall | **33.33%** | 1 TP / 3 reference decisions |
| Final-decision F1 | **50.00%** | 1 TP, 0 FP, 2 FN |
| Strict QA correctness | **66.67%** | 4 fully correct / 6; 2 incorrect |

Decision precision is based on **one prediction** and comes with low recall; it does not establish general reliability. Answerable-question correctness was 2/4 (50%); missing-information questions were 2/2 correct. No answer received partial evaluator credit. Model status labels are distinct from evaluator grades: accurately explaining missing information can fully answer a question.

| Excerpt | Duration | WER | Action TP/FP/FN | Decision TP/FP/FN | Correct QA |
|---|---:|---:|---:|---:|---:|
| ES2004a, 885–1049 s | 164 s | 22.24% (129/580) | 0/0/1 | 0/0/0 | 2/2 |
| ES2004d, 1420–1660 s | 240 s | 31.92% (248/777) | 1/2/0 | 1/0/0 | 1/2 |
| IS1003b, 1458–1614 s | 156 s | 30.21% (103/341) | 1/0/2 | 0/0/2 | 1/2 |

WER pools 94 substitutions, 356 deletions and 30 insertions. Extraction scores pool counts, not case percentages. Empty denominators remain null. Owner and absent-deadline slots were correct on the two matched tasks (2/2 each), but three tasks were missed. No positive task deadlines occur in this sample, so these checks do not establish deadline-extraction accuracy.

## Method and limits

Three previously untested project excerpts from public AMI Mix-Headset recordings total 560 seconds. References, questions, rules, settings and application hashes were frozen before inference on November 21. Application code and labels were not tuned after predictions. This is a small purposive project-held-out pilot, not an official AMI benchmark or a team-disjoint test. Model pretraining overlap is unknown.

Lexical references come from AMI manual annotations v1.6.2. Structured labels and QA expectations were authored by the coding assistant from those human transcripts before inference. Semantic adjudication was also performed by the assistant, **without independent human annotation review**. Treat these scores as provisional.

Whisper small ran locally in English on CPU with four threads, temperature zero, word timestamps and no previous-text conditioning. Pyannote community-1 used automatic speaker count and up to 300 seconds of surrounding audio per side. WER uses JiWER and Whisper EnglishTextNormalizer on both texts. Overlapping reference words are serialized by onset. Four speakers were detected per excerpt, but no DER or speaker-identification accuracy is claimed.

Gemini 2.5 Flash processed actual ASR transcripts, not corrected human text. Decisions and batched QA used draft plus review. Same-model review is inference, not independent evaluation. Final-decision scores include substantive topics with final status agreed; unresolved topics are retained but excluded from the final-agreement prediction set. See [frozen protocol](DAY_09_PROTOCOL.md).

## Findings for Day 10

- Missed tasks: presentation commitment, components work, and interface concept work. ASR loses PowerPoint and components; presentation intent and interface assignment survive partly but extraction misses them.
- False-positive tasks: work to the specification and make the price fit are constraints/design goals rather than concrete future assignments under the frozen rubric.
- Underspecified match: the head-office recommendation matches task intent but omits voice-recognition detail. Task-intent matching does not establish complete task-detail accuracy.
- Decision handling: final removal of voice recognition is captured and flip-top/colour proposals remain unresolved. Brand/fashion requirements are omitted. Teletext becomes unresolved after an ASR-derived objection. Human segment IS1003b.sync.392 is garbled; independent listening is needed to distinguish an objection from a clarification question. This provisional false negative is not definitively a model error. Frozen labels were retained.
- Incorrect QA: the removal answer retains budget 12.25/12.50, although the human reference resolves it to 12.50; ASR omitted that final clarification. The designer answer assigns both roles to interface work and interprets corrupted Florent as flow.
- Traceability: the correct all-yellow abstention places explanatory context in its limitation field without formal claim citations. Citation integrity does not ensure every displayed assertion has a citation.

These are recorded findings, not fixes silently applied to test data. No accepted task-deadline revision occurs here; positive revision accuracy cannot be claimed from this sample. Day 10 remains open for error analysis, improvements, final documentation and demonstration.

## Verification and quota

All **93 retained evidence references** match transcript IDs, quotes, timestamps and speaker IDs; source fingerprints validate. The scorer independently recalculates WER and verifies reference hashes and excerpt intervals. It rejects missing reviews, duplicate matches and stale predictions. Provenance integrity is separate from semantic correctness.

The unchanged code passed **160 tests on 2026-11-21**, including 12 Day 9 scoring/integrity tests. Complete scoring succeeded against real outputs on November 22 without API calls.

Total Gemini use: **16 attempts, 15 successful responses, one daily-quota rejection**. Fourteen successful calls completed the resumed run. No schema-repair calls were needed; the persistent 20-attempt cap was respected. The historical failure file remains, superseded by the completed decision output.

## Deliverables and reproduction

- [Machine-readable metrics](../evaluation/day09_metrics.json)
- [Frozen structured reference](../evaluation/day09_gold.json)
- [Hash-bound semantic review ledger](../evaluation/day09_adjudication.json)
- [Reproduction instructions](../evaluation/README.md)

Runtime evidence is under `C:/Users/shara/Projects/ai-meeting-intelligence/outputs/day09`. The validated `day09_evaluation_bundle.zip` includes frozen source, references, predictions, review ledger and metrics. Credentials, model weights and audio are excluded. Public audio URLs and hashes remain in provenance.

From the source repository, recompute without Gemini requests:

```powershell
$envRoot = 'C:/Users/shara/Projects/ai-meeting-intelligence'
& "$envRoot/.venv/Scripts/python.exe" scripts/score_day09.py --environment-root $envRoot
```

After application changes, extract the bundle, run from its source directory, and place its outputs/day09 beneath the chosen environment root. Use package versions in freeze.json. The hash guard intentionally rejects changed code or gold.
