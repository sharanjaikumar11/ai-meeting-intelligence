"""Score the known-case release regression; keep it distinct from unseen results."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from score_day09 import extraction_score, prf, sha
from verify_day08_live import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = a.environment_root / "outputs/day10/release_v9"
    review_path = repo / "evaluation/release_v9_review.json"
    ledger = json.loads(review_path.read_text(encoding="utf-8"))
    manifest = json.loads((out / "source_sha256.json").read_text(encoding="utf-8"))
    for rel, digest in manifest.items():
        assert sha(repo / rel) == digest, "Candidate changed"
    reports = {}
    seen = set()
    for name, folder in [("day10_unseen", "final_2026-11-23"), ("fresh_v8", "fresh_v8_ES2009a")]:
        gold_path = repo / "evaluation" / f"{name}_gold.json"
        assert sha(gold_path) == ledger["gold_sha256"][name]
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        rows = []
        correct_owners = correct_details = matches = 0
        for case in gold["cases"]:
            cid = case["id"]
            seen.add(cid)
            review = ledger["cases"][cid]
            action_path = out / f"{cid}.actions.json"
            transcript_path = (
                a.environment_root / "outputs/day10" / folder / f"{cid}.transcript.json"
            )
            assert sha(action_path) == review["actions_sha256"]
            assert sha(transcript_path) == review["transcript_sha256"]
            actions = json.loads(action_path.read_text(encoding="utf-8"))
            transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
            verify(dict(transcript=transcript, actions=actions))
            score = extraction_score(actions["action_items"], case["actions"], review["actions"])
            for item in review["actions"]:
                if item["gold_id"] is not None:
                    assert (
                        type(item["owner_correct"]) is bool and type(item["detail_correct"]) is bool
                    )
                    matches += 1
                    correct_owners += item["owner_correct"]
                    correct_details += item["detail_correct"]
            rows.append(dict(case=cid, **score))
        counts = {k: sum(r[k] for r in rows) for k in ["tp", "fp", "fn"]}
        reports[name] = dict(
            actions=prf(**counts),
            cases=rows,
            owners=dict(correct=correct_owners, total=matches),
            details=dict(correct=correct_details, total=matches),
        )
    assert seen == set(ledger["cases"])
    result = dict(
        scope="Development regression on known cases after tuning; not unseen accuracy.",
        annotation="Assistant adjudication, no independent human review.",
        review_sha256=sha(review_path),
        results=reports,
    )
    (repo / "evaluation/release_v9_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {k: {n: v[n] for n in ["actions", "owners", "details"]} for k, v in reports.items()},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
