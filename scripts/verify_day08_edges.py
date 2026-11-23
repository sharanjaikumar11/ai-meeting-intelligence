"""Real audio and API edge cases, kept separate from untouched AMI recordings."""

import argparse
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_day08_live import verify

from meeting_intelligence.media import decode, ffmpeg_tools


def prepare(root):
    folder = root / "data/day08/edge_fixtures"
    folder.mkdir(exist_ok=True)
    ffmpeg, _ = ffmpeg_tools(root)
    with wave.open(str(folder / "silence.wav"), "wb") as out:
        out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        out.writeframes(bytes(16000 * 2 * 20))
    (folder / "corrupt.wav").write_bytes(b"This deliberately is not an audio recording.")
    subprocess.run(
        [
            str(ffmpeg),
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=1:d=2",
            "-an",
            "-c:v",
            "mpeg4",
            str(folder / "no_audio.mp4"),
        ],
        check=True,
        capture_output=True,
    )
    decode(
        root / "data/recordings/ES2005a.Mix-Headset.wav", folder / "clean.wav", ffmpeg, 0, 170, 70
    )
    with wave.open(str(folder / "clean.wav")) as audio:
        signal = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float64)
    # Deterministic additive noise at 5 dB SNR; label as artificial degradation.
    noise = np.random.default_rng(8).normal(size=signal.shape)
    noise *= np.sqrt(np.mean(signal**2) / 10 ** (5 / 10)) / np.sqrt(np.mean(noise**2))
    mixed = signal + noise
    mixed *= min(1, 32000 / max(1, np.max(np.abs(mixed))))
    with wave.open(str(folder / "noisy_5db.wav"), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(mixed.astype("<i2").tobytes())
    return folder


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument(
        "--case", choices=["silence", "corrupt", "no_audio", "past_end", "clean", "noisy_5db"]
    )
    a = p.parse_args()
    folder = prepare(a.environment_root)
    output = a.environment_root / "outputs/day08"
    output.mkdir(exist_ok=True)
    reports_file = output / "edge_reports.json"
    reports = json.loads(reports_file.read_text()) if reports_file.exists() else {}

    def save():
        reports_file.write_text(json.dumps(reports, indent=2), encoding="utf-8")

    cases = [
        ("silence", "silence.wav", 0, "completed"),
        ("corrupt", "corrupt.wav", 0, "failed"),
        ("no_audio", "no_audio.mp4", 0, "failed"),
        ("past_end", "silence.wav", 25, "failed"),
        ("clean", "clean.wav", 0, "completed"),
        ("noisy_5db", "noisy_5db.wav", 0, "completed"),
    ]
    with httpx.Client(timeout=180) as client:
        for name, filename, start, expected in cases:
            if a.case and a.case != name:
                continue
            report = reports.setdefault(name, {})
            if "id" not in report:
                with (folder / filename).open("rb") as file:
                    r = client.post(
                        a.url + "/api/meetings",
                        files={"recording": (filename, file)},
                        data={"start": str(start), "diarize": "true"},
                    )
                r.raise_for_status()
                report["id"] = r.json()["id"]
                save()
            path = a.url + "/api/meetings/" + report["id"]
            previous = None
            for _ in range(900):
                r = client.get(path)
                r.raise_for_status()
                state = r.json()
                label = (state["status"], state["stage"])
                if label != previous:
                    print(name, label, flush=True)
                    previous = label
                if state["status"] in {"completed", "failed", "interrupted"}:
                    break
                time.sleep(2)
            report.update(
                status=state["status"],
                error=state["error"],
                expected_status=expected,
                status_passed=state["status"] == expected,
            )
            if state["status"] == "completed":
                result = state["result"]
                report["checks"] = verify(result)
                (output / f"edge_{name}.result.json").write_text(
                    json.dumps(result, indent=2), encoding="utf-8"
                )
                if name == "silence":
                    report["no_hallucination"] = (
                        not result["transcript"]["segments"]
                        and not result["summary"]["summary_statements"]
                        and not result["actions"]["action_items"]
                        and not result["decisions"]["topics"]
                    )
            save()
            print(name, report, flush=True)


if __name__ == "__main__":
    main()
