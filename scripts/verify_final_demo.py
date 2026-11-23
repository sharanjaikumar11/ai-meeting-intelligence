"""Resume a real upload demonstration without overwriting historical checks."""

import argparse
import json
import time
from pathlib import Path

import httpx
from verify_day08_live import verify


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument(
        "--skip-question",
        action="store_true",
        help="Verify upload stages and download only; leave live QA explicitly pending.",
    )
    a = p.parse_args()
    out = a.environment_root / "outputs/day10/final_2026-11-23"
    checkpoint = out / "demo.json"
    report = json.loads(checkpoint.read_text()) if checkpoint.exists() else {}

    def save():
        checkpoint.write_text(json.dumps(report, indent=2), encoding="utf-8")

    with httpx.Client(timeout=180) as client:
        if "meeting_id" not in report:
            with (a.environment_root / "data/day02_fixtures/ami_excerpt.mp4").open("rb") as f:
                response = client.post(
                    a.url + "/api/meetings",
                    files={"recording": ("Day10-public-AMI-demo.mp4", f, "video/mp4")},
                    data={"diarize": "true"},
                )
            response.raise_for_status()
            report["meeting_id"] = response.json()["id"]
            save()
        endpoint = a.url + "/api/meetings/" + report["meeting_id"]
        previous = None
        for _ in range(900):
            response = client.get(endpoint)
            response.raise_for_status()
            state = response.json()
            label = (state["status"], state["stage"])
            if label != previous:
                print(label, flush=True)
                previous = label
            if state["status"] in {"completed", "failed", "interrupted"}:
                break
            time.sleep(2)
        report.update(
            status=state["status"],
            stage=state["stage"],
            error=state["error"],
            stages=list(state["result"]),
        )
        save()
        if state["status"] != "completed":
            raise RuntimeError("Demo incomplete; saved job can be retried through the app.")
        download = client.get(endpoint + "/download")
        download.raise_for_status()
        assert download.json() == state["result"]
        result = download.json()
        verify(result)
        (out / "demo.result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        report["download_matches_saved_result"] = True
        if a.skip_question:
            report["live_qa_status"] = "not_run_in_this_demo_budget"
            save()
            print("Real upload and JSON download verified; live QA not run.", flush=True)
            return
        if "qa" not in report:
            answer = client.post(
                endpoint + "/questions", json={"question": "What is the purpose of this meeting?"}
            )
            answer.raise_for_status()
            report["qa"] = answer.json()
            save()
        verify(dict(transcript=result["transcript"], qa=report["qa"]))
        report["exact_evidence_verified"] = True
        save()
        print("Real-model demo completed:", report["meeting_id"], flush=True)


if __name__ == "__main__":
    main()
