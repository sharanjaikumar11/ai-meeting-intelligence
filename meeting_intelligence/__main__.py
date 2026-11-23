"""Run with python -m meeting_intelligence RECORDING --environment-root ROOT."""

import argparse
import json
import sys
from pathlib import Path

from .pipeline import transcribe


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a local audio/video meeting with timestamps and speaker labels."
    )
    parser.add_argument("recording", type=Path)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New output directory; existing directories are never overwritten.",
    )
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="en", help="Language code, or auto")
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--num-speakers", type=int)
    parser.add_argument(
        "--diarization-context",
        type=float,
        default=300,
        help="Extra surrounding audio seconds per side for speaker clustering (default: 300; use 0 for excerpt-only clustering)",
    )
    parser.add_argument(
        "--speaker-names",
        type=Path,
        help="JSON map of detected speaker IDs to user-confirmed names",
    )
    parser.add_argument("--skip-diarization", action="store_true")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument(
        "--beam-size",
        type=int,
        help="Optional Whisper beam search width, e.g. 5; slower and not guaranteed to improve accuracy.",
    )
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output directory already exists. Choose a new path.")
        names = (
            json.loads(args.speaker_names.read_text(encoding="utf-8")) if args.speaker_names else {}
        )
        if not isinstance(names, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) or not v.strip()
            for k, v in names.items()
        ):
            raise ValueError("Speaker names must be a JSON object mapping IDs to nonempty strings.")
        result = transcribe(
            args.recording,
            args.environment_root,
            args.model,
            args.language,
            args.start,
            args.duration,
            args.skip_diarization,
            args.num_speakers,
            names,
            args.threads,
            args.diarization_context,
            beam_size=args.beam_size,
        )
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "transcript.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        text = "\n".join(
            f"[{timestamp(segment.start)} - {timestamp(segment.end)}] "
            f"{segment.speaker_name or segment.speaker_id or 'UNASSIGNED'}: {segment.text}"
            for segment in result.segments
        )
        (args.output / "transcript.txt").write_text(text + "\n", encoding="utf-8")
        print(f"Saved {len(result.segments)} timestamped segments to {args.output}")
        print(f"Diarization: {result.diarization_status}; speakers: {len(result.speakers)}")
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
