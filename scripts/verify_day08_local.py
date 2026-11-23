"""Finish Day 8 audio checks without any Gemini requests."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_day08_edges import prepare
from verify_day08_live import CASES

from meeting_intelligence.action_extraction import extract_actions
from meeting_intelligence.decision_tracking import track_decisions
from meeting_intelligence.media import MediaInputError, ffmpeg_tools, probe_media
from meeting_intelligence.pipeline import transcribe, transcription_quality_warnings
from meeting_intelligence.qa import ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import summarize


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--rerun-silence", action="store_true")
    a = p.parse_args()
    root = a.environment_root
    output = root / "outputs/day08"
    path = output / "local_checks.json"
    report = json.loads(path.read_text()) if path.exists() else {}

    def save():
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for name, *_ in CASES:
        job = json.loads((output / f"{name}.json").read_text())
        data = json.loads((root / "outputs/web" / job["meeting_id"] / "result.json").read_text())
        t = Transcript.model_validate(data["transcript"])
        (output / f"{name}.transcript.json").write_text(
            t.model_dump_json(indent=2), encoding="utf-8"
        )
        report[name] = dict(
            schema_and_timeline_passed=True,
            segments=len(t.segments),
            predicted_speakers=len(t.speakers),
            overlap_segments=sum(s.overlapping_speech for s in t.segments),
            start=t.processed_start_seconds,
            duration=t.processed_duration_seconds,
        )
    save()
    folder = prepare(root)
    _, ffprobe = ffmpeg_tools(root)
    for name in ["corrupt", "no_audio"]:
        filename = "corrupt.wav" if name == "corrupt" else "no_audio.mp4"
        try:
            probe_media(folder / filename, ffprobe)
        except MediaInputError as exc:
            report[name] = dict(passed=True, message=str(exc))
        else:
            report[name] = dict(passed=False)
    try:
        transcribe(folder / "silence.wav", root, start=25)
    except MediaInputError as exc:
        report["past_end"] = dict(passed=True, message=str(exc))
    else:
        report["past_end"] = dict(passed=False)
    save()
    for name in ["silence", "clean", "noisy_5db"]:
        target = output / f"local_{name}.transcript.json"
        if target.exists() and not (name == "silence" and a.rerun_silence):
            t = Transcript.model_validate_json(target.read_text())
        else:
            if target.exists():
                backup = output / f"local_{name}.before_guard.transcript.json"
                if not backup.exists():
                    backup.write_bytes(target.read_bytes())
            print("Running real local models:", name, flush=True)
            t = transcribe(folder / f"{name}.wav", root, diarization_context=0)
            target.write_text(t.model_dump_json(indent=2), encoding="utf-8")
        report[name] = dict(
            segments=len(t.segments),
            predicted_speakers=len(t.speakers),
            overlapping_segments=sum(s.overlapping_speech for s in t.segments),
            warnings=t.warnings,
        )
        report[name]["review_heuristic"] = transcription_quality_warnings(t.segments)
        if name == "silence":
            report[name]["no_invented_speech"] = not t.segments and not t.text.strip()
            if not t.segments:
                report[name]["downstream_abstention"] = (
                    summarize(t, "not-called").generation_status == "no_speech"
                    and not extract_actions(t, "not-called").action_items
                    and not track_decisions(t, "not-called").topics
                    and ask(t, "What was agreed?").status == "not_found"
                )
        save()
        print(name, report[name], flush=True)
    print("Local checks saved; no Gemini requests made.", flush=True)


if __name__ == "__main__":
    main()
