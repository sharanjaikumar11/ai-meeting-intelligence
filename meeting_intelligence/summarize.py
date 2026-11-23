"""CLI: python -m meeting_intelligence.summarize TRANSCRIPT.json ..."""

import argparse
import sys
from pathlib import Path

from .__main__ import timestamp
from .schemas import Transcript
from .summarization import DEFAULT_MODEL, GeminiGenerator, settings_from_environment, summarize


def render_text(result):
    lines = [
        f"Scope: {result.input_scope}",
        f"Interval: {timestamp(result.processed_interval.start)} - {timestamp(result.processed_interval.end)}",
        "",
        "Meeting summary",
        result.meeting_summary or "No transcribed speech was available.",
        "",
        "Summary evidence",
    ]
    for statement in result.summary_statements:
        lines.append(f"- {statement.text}")
        for evidence in statement.evidence:
            lines.append(
                f'  [{timestamp(evidence.start)} - {timestamp(evidence.end)}] {evidence.segment_id}: "{evidence.quote}"'
            )
    lines.extend(["", "Key discussion points"])
    for point in result.key_discussion_points:
        lines.append(f"- {point.topic}: {point.detail}")
        for evidence in point.evidence:
            lines.append(
                f'  [{timestamp(evidence.start)} - {timestamp(evidence.end)}] {evidence.segment_id}: "{evidence.quote}"'
            )
    lines.extend(["", "Limitations", *[f"- {warning}" for warning in result.warnings]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Gemini meeting summary and key discussion points from Day 2 JSON."
    )
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--model", help="Overrides GEMINI_MODEL")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output directory already exists. Choose a new path.")
        transcript = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
        if any(segment.text.strip() for segment in transcript.segments):
            settings = settings_from_environment(args.environment_root, args.model)
            print(f"Generating summary with {settings.model}", flush=True)
            result = summarize(transcript, settings.model, GeminiGenerator(settings))
        else:
            result = summarize(transcript, args.model or DEFAULT_MODEL)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "summary.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        (args.output / "summary.txt").write_text(render_text(result), encoding="utf-8")
        print(
            f"Saved {len(result.summary_statements)} summary statements and {len(result.key_discussion_points)} discussion points to {args.output}"
        )
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
