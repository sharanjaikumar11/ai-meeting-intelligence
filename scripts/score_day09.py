"""Recompute objective counts from frozen outputs and explicit semantic adjudication.

Semantic equivalence is reviewed in a ledger, never guessed by string similarity.
The scorer rejects missing/duplicate reviews, many-to-one matches and stale hashes.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MISSING_INFORMATION_QUESTIONS = {("ES2004a_0885_1049", 1), ("ES2004d_1420_1660", 1)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prf(tp, fp, fn):
    if min(tp, fp, fn) < 0:
        raise ValueError("Negative counts")
    return dict(
        tp=tp,
        fp=fp,
        fn=fn,
        precision=tp / (tp + fp) if tp + fp else None,
        recall=tp / (tp + fn) if tp + fn else None,
        f1=2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None,
    )


def extraction_score(predictions, gold, reviews):
    pred_ids = [p["id"] for p in predictions]
    gold_ids = {g["id"] for g in gold}
    review_ids = [r["prediction_id"] for r in reviews]
    if len(set(pred_ids)) != len(pred_ids) or len(gold_ids) != len(gold):
        raise ValueError("Duplicate prediction/gold IDs")
    if len(set(review_ids)) != len(review_ids) or set(review_ids) != set(pred_ids):
        raise ValueError("Every prediction needs exactly one review")
    matched = []
    for r in reviews:
        if not r.get("reason", "").strip():
            raise ValueError("Review reason required")
        gid = r.get("gold_id")
        if gid is not None:
            if gid not in gold_ids or gid in matched:
                raise ValueError("Matches must be valid and one-to-one")
            matched.append(gid)
    result = prf(len(matched), len(predictions) - len(matched), len(gold) - len(matched))
    result["missed_gold_ids"] = sorted(gold_ids - set(matched))
    return result


def qa_score(gold, reviews):
    if sorted(r["question_index"] for r in reviews) != list(range(len(gold))):
        raise ValueError("Every frozen question needs exactly one review")
    counts = dict(full=0, partial=0, incorrect=0)
    for r in reviews:
        if r["grade"] not in counts or not r.get("reason", "").strip():
            raise ValueError("Invalid QA review")
        counts[r["grade"]] += 1
    return dict(**counts, total=len(gold), correctness=counts["full"] / len(gold) if gold else None)


def pool_wer(rows):
    counts = {
        k: sum(r[k] for r in rows)
        for k in ["substitutions", "deletions", "insertions", "reference_words"]
    }
    if any(v < 0 for v in counts.values()):
        raise ValueError("Negative WER counts")
    errors = sum(counts[k] for k in ["substitutions", "deletions", "insertions"])
    return dict(
        **counts,
        word_errors=errors,
        wer=errors / counts["reference_words"] if counts["reference_words"] else None,
    )


def validate_wer(out, case, transcript, saved):
    """Recalculate WER from pinned human reference and actual ASR, not saved totals."""
    import jiwer
    from whisper.normalizers import EnglishTextNormalizer

    if (
        abs(transcript.processed_start_seconds - case["start"]) > 0.001
        or abs(transcript.processed_duration_seconds - (case["end"] - case["start"])) > 0.001
    ):
        raise ValueError("Transcript interval differs from frozen reference")
    path = out / f"{case['id']}.reference.json"
    provenance = json.loads((out / "provenance.json").read_text())
    record = next(r for r in provenance["recordings"] if r["case"] == case["id"])
    if sha(path) != record["reference_sha256"]:
        raise ValueError("Human reference changed")
    reference = json.loads(path.read_text(encoding="utf-8"))
    norm = EnglishTextNormalizer()
    r, h = norm(reference["text"]), norm(transcript.text)
    m = jiwer.process_words(r, h)
    counts = dict(
        substitutions=m.substitutions,
        deletions=m.deletions,
        insertions=m.insertions,
        reference_words=m.hits + m.substitutions + m.deletions,
    )
    if (
        any(saved[k] != v for k, v in counts.items())
        or saved["reference"] != r
        or saved["hypothesis"] != h
    ):
        raise ValueError("Saved WER does not match reference and prediction")
    return pool_wer([counts])


def score(root, ledger_path):
    out = root / "outputs/day09"
    repo = Path(__file__).resolve().parents[1]
    gold_path = repo / "evaluation/day09_gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    freeze = json.loads((out / "freeze.json").read_text())
    for rel, expected in freeze["source_sha256"].items():
        if sha(repo / rel) != expected:
            raise ValueError("Frozen source changed: " + rel)
    if ledger["gold_sha256"] != sha(gold_path):
        raise ValueError("Gold hash mismatch")
    expected_cases = {c["id"] for c in gold["cases"]}
    if set(ledger["cases"]) != expected_cases:
        raise ValueError("Incomplete case ledger")
    results = []
    all_wer = []
    owner_correct = owner_total = deadline_correct = deadline_total = 0
    integrity_total = 0
    qa_groups = {
        name: dict(full=0, partial=0, incorrect=0, total=0)
        for name in ["answerable", "missing_information"]
    }
    for c in gold["cases"]:
        review = ledger["cases"][c["id"]]
        paths = {
            name: out / f"{c['id']}.{name}.json"
            for name in ["transcript", "actions", "decisions", "qa", "wer"]
        }
        # Require actual outputs for this completed report, not silently dropped failures.
        if set(review["prediction_sha256"]) != set(paths):
            raise ValueError("Incomplete hash manifest")
        for name, path in paths.items():
            if review["prediction_sha256"][name] != sha(path):
                raise ValueError("Stale prediction review: " + name)
        data = {name: json.loads(path.read_text(encoding="utf-8")) for name, path in paths.items()}
        if data["wer"]["transcript_sha256"] != sha(paths["transcript"]):
            raise ValueError("Stale WER")
        from meeting_intelligence.schemas import Transcript

        validate_wer(out, c, Transcript.model_validate(data["transcript"]), data["wer"])
        decisions = [
            t
            for t in data["decisions"]["topics"]
            if t["kind"] == "decision" and t["status"] == "agreed"
        ]
        actions = extraction_score(data["actions"]["action_items"], c["actions"], review["actions"])
        dec = extraction_score(decisions, c["decisions"], review["decisions"])
        qa = qa_score(c["qa"], review["qa"])
        for q in review["qa"]:
            group = (
                "missing_information"
                if (c["id"], q["question_index"]) in MISSING_INFORMATION_QUESTIONS
                else "answerable"
            )
            qa_groups[group][q["grade"]] += 1
            qa_groups[group]["total"] += 1
        if [q["question"] for q in data["qa"]["answers"]] != [q["question"] for q in c["qa"]]:
            raise ValueError("Question set/order changed")
        for item in review["actions"]:
            if item.get("gold_id") is not None:
                for slot in ["owner_correct", "deadline_correct"]:
                    if type(item.get(slot)) is not bool:
                        raise ValueError("Matched tasks require slot reviews")
                owner_total += 1
                deadline_total += 1
                owner_correct += item["owner_correct"]
                deadline_correct += item["deadline_correct"]
        from verify_day08_live import verify

        check = verify(
            {k: v for k, v in data.items() if k in ["transcript", "actions", "decisions"]}
        )
        checks = [
            verify({"transcript": data["transcript"], "qa": v}) for v in data["qa"]["answers"]
        ]
        evidence = check["verified_evidence"] + sum(v["verified_evidence"] for v in checks)
        integrity_total += evidence
        all_wer.append(data["wer"])
        results.append(
            dict(
                case=c["id"],
                audio_seconds=c["end"] - c["start"],
                wer=pool_wer([data["wer"]]),
                actions=actions,
                decisions=dec,
                qa=qa,
                integrity=dict(
                    evidence_references_verified=evidence,
                    predicted_speakers=check["predicted_speakers"],
                ),
            )
        )
    aggregate = {
        key: prf(*(sum(r[key][k] for r in results) for k in ["tp", "fp", "fn"]))
        for key in ["actions", "decisions"]
    }
    qcounts = {
        k: sum(r["qa"][k] for r in results) for k in ["full", "partial", "incorrect", "total"]
    }
    aggregate.update(
        wer=pool_wer(all_wer),
        qa=dict(**qcounts, correctness=qcounts["full"] / qcounts["total"]),
        qa_by_question_type={
            name: dict(
                **counts, correctness=counts["full"] / counts["total"] if counts["total"] else None
            )
            for name, counts in qa_groups.items()
        },
        owner_on_matched_tasks=dict(
            correct=owner_correct,
            total=owner_total,
            accuracy=owner_correct / owner_total if owner_total else None,
        ),
        missing_deadline_on_matched_tasks=dict(
            correct=deadline_correct,
            total=deadline_total,
            accuracy=deadline_correct / deadline_total if deadline_total else None,
            positive_deadline_examples=0,
        ),
        evidence_references_verified=integrity_total,
    )
    attempts = json.loads((out / "request_ledger.json").read_text())
    report = dict(
        status="completed_small_pilot",
        annotation_method=gold["annotation_method"],
        protocol="docs/DAY_09_PROTOCOL.md",
        freeze_sha256=sha(out / "freeze.json"),
        gold_sha256=sha(gold_path),
        adjudication_sha256=sha(ledger_path),
        scorer_sha256=sha(Path(__file__)),
        gemini_attempts=len(attempts),
        gemini_successful_responses=sum(e["status"] == "completed" for e in attempts),
        audio_seconds=sum(r["audio_seconds"] for r in results),
        aggregate=aggregate,
        cases=results,
        limitations=[
            "Small purposive project-held-out pilot; not official AMI benchmark or team-disjoint split.",
            "Structured gold and semantic adjudication authored by assistant, not independently human-validated.",
            "No positive task deadlines or accepted deadline revisions; no positive deadline accuracy claim.",
            "WER uses onset-serialized overlapping speech; diarization error rate not measured.",
            "QA is six fixed questions using batched draft/review inference.",
            "Source citation integrity is not semantic accuracy.",
        ],
    )
    return report


def score_local(root):
    """Publish completed local measurements without inventing unavailable LLM scores."""
    out = root / "outputs/day09"
    repo = Path(__file__).resolve().parents[1]
    frozen = json.loads((out / "freeze.json").read_text())
    for rel, expected in frozen["source_sha256"].items():
        if sha(repo / rel) != expected:
            raise ValueError("Frozen source changed: " + rel)
    gold = json.loads((repo / "evaluation/day09_gold.json").read_text(encoding="utf-8"))
    rows = []
    for c in gold["cases"]:
        path = out / f"{c['id']}.transcript.json"
        w = json.loads((out / f"{c['id']}.wer.json").read_text())
        if w["transcript_sha256"] != sha(path):
            raise ValueError("Stale WER")
        from meeting_intelligence.schemas import Transcript

        t = Transcript.model_validate_json(path.read_text(encoding="utf-8"))
        verified_wer = validate_wer(out, c, t, w)
        rows.append(
            dict(
                case=c["id"],
                audio_seconds=c["end"] - c["start"],
                wer=verified_wer,
                predicted_speakers=len(t.speakers),
                segments=len(t.segments),
                transcript_sha256=sha(path),
                available_model_stages=[
                    s
                    for s in ["actions", "decisions", "qa"]
                    if (out / f"{c['id']}.{s}.json").exists()
                ],
            )
        )
    attempts = (
        json.loads((out / "request_ledger.json").read_text())
        if (out / "request_ledger.json").exists()
        else []
    )
    return dict(
        status="local_evaluation_complete_gemini_pending",
        annotation_method=gold["annotation_method"],
        frozen_source_verified=True,
        freeze_sha256=sha(out / "freeze.json"),
        audio_seconds=sum(r["audio_seconds"] for r in rows),
        aggregate_wer=pool_wer([r["wer"] for r in rows]),
        cases=rows,
        action_precision_recall_f1=None,
        decision_precision_recall_f1=None,
        qa_correctness=None,
        pending_reason="Project daily Gemini quota exhausted; user chose to resume after reset. Run paused, not a completed semantic evaluation.",
        gemini_attempts=len(attempts),
        gemini_successful_responses=sum(e["status"] == "completed" for e in attempts),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument(
        "--ledger",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "evaluation/day09_adjudication.json",
    )
    p.add_argument(
        "--local-only",
        action="store_true",
        help="Score all ASR clips while explicitly leaving LLM metrics unavailable.",
    )
    a = p.parse_args()
    report = (
        score_local(a.environment_root) if a.local_only else score(a.environment_root, a.ledger)
    )
    out = (
        a.environment_root
        / "outputs/day09"
        / ("local_metrics.json" if a.local_only else "metrics.json")
    )
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report.get("aggregate", report.get("aggregate_wer")), indent=2))


if __name__ == "__main__":
    main()
