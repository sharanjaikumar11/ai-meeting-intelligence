"""Revalidate recorded model outputs with local guards; NO network/model calls.

Preserves pre-guard and original web results. Publication only occurs after
explicit review assertions pass and none of these web jobs is running.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_day08_live import CASES, verify

from meeting_intelligence.action_extraction import extract_actions, guard_product_choices
from meeting_intelligence.action_schemas import MeetingActions
from meeting_intelligence.decision_tracking import track_decisions
from meeting_intelligence.qa import Answer, guard_qa_ownership
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import Generation, SummaryError


def write(path, value):
    temporary = path.with_suffix(".day08.tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--publish", action="store_true")
    a = p.parse_args()
    root = a.environment_root
    folder = root / "outputs/day08/completion_2026-11-20"
    final = {}
    qa = {}
    report = {
        "network_calls": 0,
        "method": "Local deterministic validation/reduction of saved real Gemini outputs, followed by explicit reference-based semantic review.",
    }
    for name, *_ in CASES:
        path = folder / f"{name}.result.json"
        backup = folder / f"{name}.before_local_guards.result.json"
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
        result = json.loads(backup.read_text())
        t = Transcript.model_validate(result["transcript"])
        result["actions"] = guard_product_choices(
            MeetingActions.model_validate(result["actions"])
        ).model_dump(mode="json")
        original = result["decisions"]
        topics = []
        for topic in original["topics"]:
            indices = {e["id"]: i for i, e in enumerate(topic["events"])}
            topics.append(
                dict(
                    topic=topic["topic"],
                    kind=topic["kind"],
                    events=[
                        dict(
                            type=e["type"],
                            statement=e["statement"],
                            anchor_segment_id=e["anchor_segment_id"],
                            evidence=[{"segment_id": r["segment_id"]} for r in e["evidence"]],
                            deadline_text=e["deadline"]["text"] if e["deadline"] else None,
                            resolves=[indices[id] for id in e["resolves"]],
                        )
                        for e in topic["events"]
                    ],
                )
            )

        class RecordedResponse:
            def generate(self, payload):
                return Generation(
                    json.dumps({"topics": topics}), original["model_version"], original["usage"]
                )

        revised = track_decisions(t, original["model"], RecordedResponse())
        revised.warnings.append(
            "Saved real-model events were replayed through updated local validation/state reduction; no additional model request was made."
        )
        result["decisions"] = revised.model_dump(mode="json")
        qpath = folder / f"{name}.qa.json"
        qbackup = folder / f"{name}.before_local_guards.qa.json"
        if not qbackup.exists():
            qbackup.write_bytes(qpath.read_bytes())
        answers = json.loads(qbackup.read_text())
        answers["answers"] = [
            guard_qa_ownership(Answer.model_validate(value), t).model_dump(mode="json")
            for value in answers["answers"]
        ]
        checks = verify(result)
        checks["qa_evidence"] = [
            verify({"transcript": result["transcript"], "qa": value})["verified_evidence"]
            for value in answers["answers"]
        ]
        report[name] = checks
        final[name] = result
        qa[name] = answers
    # These checks encode the completed manual review, not independent benchmark labels.
    es = final["ES2005a_full"]
    assert len(es["actions"]["action_items"]) == 4
    assert all(
        x["owner"]["kind"] == "unknown" and x["deadline"]["text"] is None
        for x in es["actions"]["action_items"]
    )
    assert all(t["status"] != "agreed" for t in es["decisions"]["topics"])
    assert qa["ES2005a_full"]["answers"][0]["status"] == "partial"
    assert "SPEAKER_" not in qa["ES2005a_full"]["answers"][0]["answer"]
    old = json.loads((root / "outputs/day08/ES2005a_full.json").read_text())
    assert old["unanswerable_qa"]["status"] == "not_found"
    report["ES2005a_full"]["abstention"] = (
        "Reused previously verified unanswerable-question result; no duplicate API call."
    )
    is_result = final["IS1001b_decisions"]
    assert len(is_result["actions"]["action_items"]) == 3
    assert any(
        t["status"] == "agreed" and "wheel" in (t["final_agreed_decision"] or "")
        for t in is_result["decisions"]["topics"]
    )
    assert qa["IS1001b_decisions"]["answers"][1]["status"] == "not_found"
    ts = final["TS3005d_revisions"]
    assert not ts["actions"]["action_items"]
    assert sum(t["status"] == "agreed" for t in ts["decisions"]["topics"]) == 3
    assert qa["TS3005d_revisions"]["answers"][1]["status"] == "not_found"
    report["semantic_review"] = {
        "ES2005a": "Research work retained; names/deadlines remain unknown; ambiguous owners and unsupported monetary recall omitted. No final design consensus invented.",
        "IS1001b": "Summary-writing/sharing and email requests retained; wheel agreement survives withdrawal of the ball proposal; QA correctly excludes LCD and speech control. Negative feature choices appear as withdrawn topics, not positive inclusion.",
        "TS3005d": "Final curve retained; speech recognition and scroll wheel dropped; no product choices presented as follow-up tasks. Correct supported answer and abstention checked against reference turns around 1774–1799 seconds.",
        "limits": "No claim of full accuracy. Some implicit tasks/owner information may be omitted by conservative guards. Speaker and ASR errors remain; WER/F1 are Day 9 work.",
    }
    noisy = Transcript.model_validate_json(
        (root / "outputs/day08/local_noisy_5db.transcript.json").read_text()
    )

    class Forbidden:
        def generate(self, payload):
            raise AssertionError("No cloud call allowed for severely uncertain transcript")

    try:
        extract_actions(noisy, "not-called", Forbidden())
    except SummaryError as exc:
        assert "Transcript needs audio review" in str(exc)
        report["noisy_audio"] = {
            "quality_gate_passed": True,
            "gemini_calls": 0,
            "message": str(exc),
        }
    else:
        raise AssertionError("Noisy transcript was not gated")
    ledger = json.loads((folder / "request_ledger.json").read_text())
    assert len(ledger) <= 20
    report["requests_attempted"] = len(ledger)
    report["api_responses_received"] = sum(e["status"] == "completed" for e in ledger)
    report["ts_review_method"] = (
        "One bundled real model request, local validators, and manual comparison to human transcript; no second model-review call."
    )
    jobs = {}
    for name in final:
        original = json.loads((root / "outputs/day08" / f"{name}.json").read_text())
        job = root / "outputs/web" / original["meeting_id"]
        state = json.loads((job / "state.json").read_text())
        assert state["status"] not in {"queued", "processing"}, "Do not overwrite an active job"
        jobs[name] = (job, state)
    for name, result in final.items():
        write(folder / f"{name}.result.json", result)
        write(folder / f"{name}.qa.json", qa[name])
        if a.publish:
            job, state = jobs[name]
            for filename in ["result.json", "state.json"]:
                backup = job / (filename + ".before_day08_completion")
                if not backup.exists():
                    backup.write_bytes((job / filename).read_bytes())
            state.update(status="completed", stage="Ready", error=None)
            write(job / "result.json", result)
            write(job / "state.json", state)
            canonical = root / "outputs/day08" / f"{name}.json"
            previous = json.loads(canonical.read_text())
            backup = canonical.with_name(canonical.stem + ".before_completion.json")
            if not backup.exists():
                backup.write_bytes(canonical.read_bytes())
            previous.update(
                status="completed",
                stage="Ready",
                error=None,
                checks=verify(result),
                supported_qa=qa[name]["answers"][0],
                review_report=str(folder / "final_review.json"),
            )
            if len(qa[name]["answers"]) > 1:
                previous["unanswerable_qa"] = qa[name]["answers"][1]
            previous["abstention_passed"] = previous["unanswerable_qa"]["status"] == "not_found"
            previous.pop("supported_qa_error", None)
            previous.pop("unanswerable_qa_error", None)
            write(canonical, previous)
            canonical_result = root / "outputs/day08" / f"{name}.result.json"
            baseline = canonical_result.with_name(canonical_result.stem + ".before_completion.json")
            if canonical_result.exists() and not baseline.exists():
                baseline.write_bytes(canonical_result.read_bytes())
            write(canonical_result, result)
        report[name]["status"] = "reviewed_and_verified"
    report["published_to_web"] = a.publish
    write(folder / "final_review.json", report)
    write(folder / "run.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
