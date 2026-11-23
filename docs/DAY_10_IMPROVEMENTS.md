# Accuracy improvement check — 2026-11-22

Task extraction improved on the **same three known Day 9 examples**. This is a development recheck after inspecting the errors, not independent evidence of generalization. Original Day 9 labels, predictions, metrics and evidence bundle remain unchanged. Day 10 as a whole is not yet complete.

## Measured task-intent results

| Measure | Day 9 baseline | New prompt alone | New prompt + final local filters |
|---|---:|---:|---:|
| True positives | 2 | 4 | 4 |
| False positives | 2 | 3 | 0 |
| False negatives | 3 | 1 | 1 |
| Precision | 50.00% | 57.14% | 100.00% |
| Recall | 40.00% | 80.00% | 80.00% |
| F1 | 44.44% | 66.67% | **88.89%** |

The final sample has only four predicted tasks. Its 100% precision is not a production guarantee. The original frozen task-intent matching rubric is used; this does not measure complete task descriptions. The recommendation still omits its subject, and the interface task still includes the unsupported qualifier “flow.” Matched-owner correctness is **3/4**: the recommendation owner regressed from group to unknown. These limits must accompany the improved F1.

## Changes retained

Action prompt version `day10-actions-v6` recognizes concrete work obligations expressed indirectly and follows assignments across split ASR turns. It preserves clear role/task pairs even when an adjacent role's assignment is unintelligible. It distinguishes executable work from vague constraints.

The existing conservative product-choice filter now catches unassigned specification-change proposals and feature-removal wording using “take … out.” It does not treat taking measurements as removal. A separate check omits announcements about closing/opening the current meeting while preserving future meeting duties with timing evidence. Explicit follow-up requests, owners and deadlines continue to protect real work from these filters.

These filters were refined after observing new false positives. Their outputs are therefore development results. Raw generated actions are preserved separately from deterministic filtered results; no task text was manually replaced with reference answers. The original and final code fingerprints, prediction hashes, and semantic review reasons are saved.

## QA experiment not adopted

A prompt experiment attempted to separate ambiguous role assignments, avoid unnecessary uncertain numbers, and keep explanations in cited claims. It still assigned both designers the interface task. The reviewed batch also violated the abstention schema and needed one repair call. The experiment was rejected; **production QA was restored byte-for-byte to its Day 9 version**. The intended additional budget-answer probe was not run because the repair consumed the remaining allowance.

No QA-score improvement is claimed. Decision extraction and ASR were not changed. Their previous measured scores remain the latest baseline results. The components task is absent from ASR; extracting it without new audio evidence would require guessing.

## Validation and quota

**169 tests passed** in the final regression run. Nine new cases cover current versus future meeting conduct, feature choices versus explicit work requests, and preserving measurement tasks. An earlier background-job test timed out, passed its isolated rerun, and passed subsequent full suites; no unrelated web code or timeout was changed.

Six Gemini attempts were used for this check: three action calls, a QA draft/review pair, and one QA schema repair. Together with the 14 successful Day 9 completion calls earlier today, this reaches the planned 20-attempt daily allowance for this thread. No further calls were made. Other project clients' usage is not observable here.

## Artifacts and local reproduction

- [Development metric counts](../evaluation/day10_action_metrics.json)
- [Hash-bound action reviews](../evaluation/day10_action_review.json)
- [Original Day 9 report](DAY_09.md)

Runtime folder: `C:/Users/shara/Projects/ai-meeting-intelligence/outputs/day10/improvement_2026-11-22`. Original responses are in `calls`, original action JSON files are at the folder root, and filtered actions are in `filtered`. The run configuration records the initial experiment; `metrics.json` records the final filter source hashes and QA rollback. These are intentionally different stages.

Recompute the development comparison without Gemini:

```powershell
$envRoot = 'C:/Users/shara/Projects/ai-meeting-intelligence'
& "$envRoot/.venv/Scripts/python.exe" scripts/score_day10_improvements.py --environment-root $envRoot
```

The original Day 9 scorer requires its frozen source; use `day09_evaluation_bundle.zip` rather than the changed application checkout to reproduce that baseline. Live experiment scripts enforce their saved source fingerprint and six-attempt cap; do not delete the ledger to bypass either check.

Next validation should use previously unseen, independently reviewed examples. Further accuracy work should address missing ASR content, role/task association, recommendation ownership and unsupported task qualifiers before claiming broadly improved meeting intelligence.
