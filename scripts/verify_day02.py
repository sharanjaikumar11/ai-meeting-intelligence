"""Verify the real Day 2 demonstrations; not a diarization accuracy benchmark."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.schemas import Transcript


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.environment_root / "outputs" / "day02"
    reports = []
    for name, start, duration, status in [
        ("audio_excerpt", 60, 120, "skipped"),
        ("video_excerpt", 0, 60, "skipped"),
        ("speaker_demo", 60, 120, "completed"),
    ]:
        output = root / name
        transcript = Transcript.model_validate_json(
            (output / "transcript.json").read_text(encoding="utf-8")
        )
        assert transcript.segments, f"{name}: no transcript segments"
        assert transcript.processed_start_seconds == start
        assert abs(transcript.processed_duration_seconds - duration) < 0.1
        assert transcript.diarization_status == status
        assert (output / "transcript.txt").read_text(encoding="utf-8").strip()
        if status == "completed":
            assert transcript.diarization_model == "pyannote/speaker-diarization-community-1"
            assert len(transcript.speakers) >= 2, (
                "Multi-speaker excerpt did not produce multiple speakers"
            )
            assert transcript.diarization_turns and transcript.exclusive_diarization_turns
            assert any(segment.speaker_id is not None for segment in transcript.segments)
            assert all(speaker.name is None for speaker in transcript.speakers), (
                "Demo must not infer real names"
            )
        else:
            assert not transcript.speakers
            assert all(segment.speaker_id is None for segment in transcript.segments)
        reports.append(
            {
                "run": name,
                "segments": len(transcript.segments),
                "words": sum(len(segment.words) for segment in transcript.segments),
                "start": start,
                "duration": duration,
                "diarization_status": status,
                "speakers": len(transcript.speakers),
                "segments_by_speaker": dict(
                    Counter(segment.speaker_id or "UNASSIGNED" for segment in transcript.segments)
                ),
                "overlapping_segments": sum(
                    segment.overlapping_speech for segment in transcript.segments
                ),
                "schema_and_bounds": "passed",
            }
        )
    reference = json.loads(
        (args.environment_root / "data" / "references" / "ES2002a.json").read_text(encoding="utf-8")
    )
    expected_speakers = len(
        {
            word["speaker_id"]
            for word in reference["words"]
            if 60 <= (word["start"] + word["end"]) / 2 < 180
        }
    )
    report = {
        "real_inference": reports,
        "diarization_inference": "passed",
        "day_2_functional_checks": "passed",
        "day_2_complete": True,
        "speaker_count_check": {
            "reference": expected_speakers,
            "predicted": reports[-1]["speakers"],
            "matches": expected_speakers == reports[-1]["speakers"],
        },
        "limitation": "Functional validation on development excerpts; not Day 9 quality evaluation.",
    }
    (root / "speaker-validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (root / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
