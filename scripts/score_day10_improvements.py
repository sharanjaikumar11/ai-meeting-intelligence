"""Score the recorded known-example experiment, including deterministic guard replay."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from score_day09 import extraction_score, prf
from verify_day08_live import verify

from meeting_intelligence.action_extraction import guard_product_choices
from meeting_intelligence.action_schemas import MeetingActions


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    out = a.environment_root / "outputs/day10/improvement_2026-11-22"
    filtered = out / "filtered"
    filtered.mkdir(exist_ok=True)
    gold = json.loads((REPO / "evaluation/day09_gold.json").read_text())
    baseline = json.loads((REPO / "evaluation/day09_metrics.json").read_text())
    if sha(REPO / "evaluation/day09_gold.json") != baseline["gold_sha256"]:
        raise ValueError("Original gold changed")
    ledger = json.loads((REPO / "evaluation/day10_action_review.json").read_text())
    rows = []
    owners = 0
    matched = 0
    for c in gold["cases"]:
        path = out / f"{c['id']}.actions.json"
        review = ledger["cases"][c["id"]]
        if sha(path) != review["raw_prediction_sha256"]:
            raise ValueError("Stale semantic review")
        original = MeetingActions.model_validate_json(path.read_text())
        result = guard_product_choices(original)
        dest = filtered / path.name
        dest.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        t = json.loads(
            (a.environment_root / "outputs/day09" / f"{c['id']}.transcript.json").read_text()
        )
        integrity = verify(dict(transcript=t, actions=result.model_dump(mode="json")))
        raw = extraction_score(
            [x.model_dump() for x in original.action_items], c["actions"], review["actions"]
        )
        ids = {x.id for x in result.action_items}
        kept = [r for r in review["actions"] if r["prediction_id"] in ids]
        after = extraction_score([x.model_dump() for x in result.action_items], c["actions"], kept)
        for r in kept:
            if r["gold_id"] is not None:
                matched += 1
                owners += r["owner_correct"]
        rows.append(
            dict(
                case=c["id"],
                raw_prompt_result=raw,
                with_final_guards=after,
                integrity=integrity,
                filtered_sha256=sha(dest),
            )
        )
    aggregate = {
        key: prf(*(sum(r[key][k] for r in rows) for k in ["tp", "fp", "fn"]))
        for key in ["raw_prompt_result", "with_final_guards"]
    }
    requests = json.loads((out / "request_ledger.json").read_text())
    report = dict(
        scope="Development recheck on known Day 9 examples, not a new held-out score",
        baseline_actions=baseline["aggregate"]["actions"],
        **aggregate,
        cases=rows,
        owner_on_matched=dict(correct=owners, total=matched),
        gemini_attempts=len(requests),
        qa_experiment="Not adopted: wrong joint role assignment persisted and review had a schema error requiring one repair. Baseline QA prompt restored. Planned one-pass ES2004d probe not run because repair consumed final budget attempt.",
        unchanged=[
            "ASR and its WER",
            "Decision extraction",
            "Production QA after experiment rollback",
            "Original Day 9 gold and metrics",
        ],
        source_sha256={
            str(f.relative_to(REPO)): sha(f)
            for f in [
                REPO / "meeting_intelligence/action_extraction.py",
                REPO / "meeting_intelligence/action_schemas.py",
                REPO / "meeting_intelligence/qa.py",
                Path(__file__),
            ]
        },
        review_sha256=sha(REPO / "evaluation/day10_action_review.json"),
        limitations=[
            "Same examples used to diagnose and refine changes; no independent generalization claim.",
            "Task intent only: interface task still contains unsupported flow qualifier; recommendation subject remains underspecified.",
            "Recommendation owner regressed from group to unknown; matched-owner accuracy must be reported.",
            "Components assignment is absent from ASR and remains missed.",
            "Conservative filters can omit implicit tasks; no claim of perfect precision outside this small sample.",
        ],
    )
    (out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "baseline_actions",
                    "raw_prompt_result",
                    "with_final_guards",
                    "owner_on_matched",
                    "gemini_attempts",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
