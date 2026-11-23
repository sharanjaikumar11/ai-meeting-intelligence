"""Public AMI fixture through the running local API; no mocked model calls."""

import argparse
import json
import time
from pathlib import Path

import httpx

p = argparse.ArgumentParser()
p.add_argument("--environment-root", type=Path, required=True)
p.add_argument("--url", default="http://127.0.0.1:8001")
a = p.parse_args()
root = a.environment_root
with httpx.Client(timeout=180) as c:
    with (root / "data/day02_fixtures/ami_excerpt.mp4").open("rb") as recording:
        r = c.post(
            a.url + "/api/meetings",
            files={"recording": ("public-AMI-excerpt.mp4", recording, "video/mp4")},
            data={"diarize": "true"},
        )
    r.raise_for_status()
    id = r.json()["id"]
    print("Meeting:", id, flush=True)
    previous = None
    for _ in range(900):
        response = c.get(a.url + "/api/meetings/" + id)
        response.raise_for_status()
        state = response.json()
        label = (state["status"], state["stage"])
        if label != previous:
            print(label, flush=True)
            previous = label
        if state["status"] in {"completed", "failed", "interrupted"}:
            break
        time.sleep(2)
    report = {
        "meeting_id": id,
        "status": state["status"],
        "stage": state["stage"],
        "error": state["error"],
        "stages": list(state["result"]),
    }
    if state["status"] == "completed":
        download = c.get(a.url + f"/api/meetings/{id}/download")
        download.raise_for_status()
        assert download.json() == state["result"]
        answer = c.post(
            a.url + f"/api/meetings/{id}/questions",
            json={"question": "What is the purpose of this meeting?"},
        )
        answer.raise_for_status()
        report["qa"] = answer.json()
        assert report["qa"]["claims"]
    output = root / "outputs/day07"
    output.mkdir(exist_ok=True)
    (output / "live_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)
    if state["status"] != "completed":
        raise SystemExit(1)
