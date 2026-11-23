"""Recompute the frozen unseen-task experiment from a hash-bound review ledger."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from score_day09 import extraction_score, pool_wer, prf, sha, validate_wer
from verify_day08_live import verify

from meeting_intelligence.schemas import Transcript


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = a.environment_root / "outputs/day10/final_2026-11-23"
    gold_path = repo / "evaluation/day10_unseen_gold.json"
    review_path = repo / "evaluation/day10_unseen_review.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    ledger = json.loads(review_path.read_text(encoding="utf-8"))
    freeze = json.loads((out / "freeze.json").read_text(encoding="utf-8"))
    for rel, expected in freeze["source_sha256"].items():
        if sha(repo / rel) != expected:
            raise ValueError("Frozen candidate changed: " + rel)
    if ledger["gold_sha256"] != sha(gold_path):
        raise ValueError("Gold changed after review")
    if set(ledger["cases"]) != {c["id"] for c in gold["cases"]}:
        raise ValueError("Review must cover every frozen case")
    rows, wers = [], []
    owners = details = matched = citations = 0
    for case in gold["cases"]:
        review = ledger["cases"][case["id"]]
        data = {}
        failed = review.get("failure")
        kinds = ["transcript", "wer"] if failed else ["transcript", "actions", "wer"]
        for kind in kinds:
            path = out / f"{case['id']}.{kind}.json"
            if review["prediction_sha256"][kind] != sha(path):
                raise ValueError("Stale review: " + str(path))
            data[kind] = json.loads(path.read_text(encoding="utf-8"))
        if data["wer"]["transcript_sha256"] != sha(out / f"{case['id']}.transcript.json"):
            raise ValueError("Stale WER")
        wer = validate_wer(out, case, Transcript.model_validate(data["transcript"]), data["wer"])
        if failed:
            if (out / f"{case['id']}.actions.json").exists():
                raise ValueError("Failure review is stale: an output now exists")
            for rel, expected in failed["artifact_sha256"].items():
                if sha(out / rel) != expected:
                    raise ValueError("Failure evidence changed")
            predictions = []
        else:
            integrity = verify({k: data[k] for k in ["transcript", "actions"]})
            citations += integrity["verified_evidence"]
            predictions = data["actions"]["action_items"]
        score = extraction_score(predictions, case["actions"], review["actions"])
        for item in review["actions"]:
            if item["gold_id"] is not None:
                if any(type(item.get(k)) is not bool for k in ["owner_correct", "detail_correct"]):
                    raise ValueError("Matched tasks require owner and detail reviews")
                matched += 1
                owners += item["owner_correct"]
                details += item["detail_correct"]
        rows.append(dict(case=case["id"], actions=score, wer=wer, pipeline_failed=bool(failed)))
        wers.append(wer)
    totals = {k: sum(r["actions"][k] for r in rows) for k in ["tp", "fp", "fn"]}
    result = dict(
        scope=gold["scope"],
        annotation=ledger["annotation"],
        gold_sha256=sha(gold_path),
        review_sha256=sha(review_path),
        cases=rows,
        actions=prf(**totals),
        wer=pool_wer(wers),
        owner_correct=dict(correct=owners, matched_tasks=matched),
        detail_correct=dict(correct=details, matched_tasks=matched),
        exact_evidence_verified=citations,
        limitations=[
            "Small purposive kickoff-meeting sample; not general meeting accuracy.",
            "Assistant semantic adjudication; no independent human review.",
            "No positive deadlines in this set; no deadline accuracy estimate.",
            "Task-intent scoring does not imply correct owner or complete detail.",
        ],
    )
    (repo / "evaluation/day10_unseen_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: result[k] for k in ["actions", "wer", "owner_correct", "detail_correct"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
