"""Resumable real-model Day 8 API exercise; no mocked outputs or auto-retries."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.schemas import Transcript

CASES = [
    (
        "ES2005a_full",
        "ES2005a.Mix-Headset.wav",
        0,
        None,
        "What research tasks were assigned, to whom, and with what deadlines?",
    ),
    (
        "IS1001b_decisions",
        "IS1001b.Mix-Headset.wav",
        1700,
        390,
        "Will the remote include an LCD screen and speech recognition? What was decided?",
    ),
    (
        "TS3005d_revisions",
        "TS3005d.Mix-Headset.wav",
        1500,
        310,
        "What is the final decision in this excerpt about the curve, speech recognition and scroll wheel?",
    ),
]


def verify(result):
    t = Transcript.model_validate(result["transcript"])
    fingerprint = hashlib.sha256(t.model_dump_json().encode()).hexdigest()
    lookup = {s.id: s for s in t.segments}
    count = 0

    def walk(value):
        nonlocal count
        if isinstance(value, dict):
            if "segment_id" in value and "quote" in value:
                s = lookup[value["segment_id"]]
                assert (value["quote"], value["start"], value["end"], value["speaker_id"]) == (
                    s.text,
                    s.start,
                    s.end,
                    s.speaker_id,
                )
                count += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for key, value in result.items():
        if key != "transcript":
            assert value["source_transcript_sha256"] == fingerprint
            walk(value)
    return dict(
        verified_evidence=count,
        transcript_segments=len(t.segments),
        predicted_speakers=len(t.speakers),
        overlap_segments=sum(s.overlapping_speech for s in t.segments),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument("--case", choices=[c[0] for c in CASES])
    p.add_argument(
        "--retry-failed",
        action="store_true",
        help="Explicitly resume saved stages after model quota/access is available.",
    )
    a = p.parse_args()
    output = a.environment_root / "outputs/day08"
    output.mkdir(exist_ok=True)
    with httpx.Client(timeout=180) as client:
        for name, filename, start, duration, question in CASES:
            if a.case and a.case != name:
                continue
            report_path = output / f"{name}.json"
            report = json.loads(report_path.read_text()) if report_path.exists() else {}

            def save():
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

            if "meeting_id" not in report:
                data = {"start": str(start), "diarize": "true"}
                if duration is not None:
                    data["duration"] = str(duration)
                with (a.environment_root / "data/recordings" / filename).open("rb") as audio:
                    r = client.post(
                        a.url + "/api/meetings",
                        files={"recording": (filename, audio, "audio/wav")},
                        data=data,
                    )
                r.raise_for_status()
                report.update(case=name, meeting_id=r.json()["id"], start=start, duration=duration)
                save()
            path = a.url + "/api/meetings/" + report["meeting_id"]
            if a.retry_failed:
                current_state = client.get(path)
                current_state.raise_for_status()
                if current_state.json()["status"] in {"failed", "interrupted"}:
                    resumed = client.post(path + "/retry")
                    resumed.raise_for_status()
            previous = None
            for _ in range(1800):
                r = client.get(path)
                r.raise_for_status()
                state = r.json()
                current = (state["status"], state["stage"])
                if current != previous:
                    print(name, current, flush=True)
                    previous = current
                if state["status"] in {"completed", "failed", "interrupted"}:
                    break
                time.sleep(2)
            report.update(status=state["status"], stage=state["stage"], error=state["error"])
            save()
            if state["status"] != "completed":
                print(json.dumps(report), flush=True)
                if "daily quota" in (state.get("error") or "").lower():
                    raise SystemExit("Daily quota exhausted; remaining meetings were not retried.")
                continue
            result = state["result"]
            report["checks"] = verify(result)
            r = client.get(path + "/download")
            r.raise_for_status()
            assert r.json() == result
            (output / f"{name}.result.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            for key, query in [
                ("supported_qa", question),
                ("unanswerable_qa", "What is the confirmed bank account number for the project?"),
            ]:
                if key not in report:
                    answer = client.post(path + "/questions", json={"question": query})
                    if answer.status_code != 200:
                        report[key + "_error"] = dict(
                            status=answer.status_code, detail=answer.json()
                        )
                        save()
                        continue
                    report[key] = answer.json()
                    report.pop(key + "_error", None)
                report[key + "_evidence"] = verify(
                    {"transcript": result["transcript"], "qa": report[key]}
                )["verified_evidence"]
                if key == "unanswerable_qa":
                    report["abstention_passed"] = (
                        report[key]["status"] == "not_found" and not report[key]["claims"]
                    )
                save()
            print(
                name, report["checks"], "abstention:", report.get("abstention_passed"), flush=True
            )


if __name__ == "__main__":
    main()
