"""CLI for Day 5 decision and deadline histories."""

import argparse
import sys
from datetime import date
from pathlib import Path

from .decision_tracking import (
    INSTRUCTION,
    DecisionReviewGenerator,
    GeneratedDecisions,
    track_decisions,
)
from .schemas import Transcript
from .summarization import DEFAULT_MODEL, GeminiGenerator, settings_from_environment


def render_text(result):
    lines = [f"Scope: {result.input_scope}", "Decision and deadline histories"]
    for topic in result.topics:
        lines.extend(
            [
                "",
                f"{topic.id}: {topic.topic} ({topic.kind}; {topic.status})",
                f"Final agreed outcome: {topic.final_agreed_decision or 'Not established'}",
            ]
        )
        if topic.final_deadline:
            lines.append(
                f"Final deadline: {topic.final_deadline.text}; date: {topic.final_deadline.date_iso or 'unresolved'}"
            )
        for event in topic.events:
            lines.append(f"- {event.id} [{event.type}] {event.statement}")
            if event.supersedes:
                lines.append(f"  Supersedes: {event.supersedes}")
            if event.resolves:
                lines.append(f"  Resolves: {', '.join(event.resolves)}")
            for ref in event.evidence:
                lines.append(f"  [{ref.start:.2f}-{ref.end:.2f}] {ref.segment_id}: {ref.quote}")
        lines.append(f"Unresolved events: {', '.join(topic.unresolved_event_ids) or 'None'}")
    return "\n".join(lines + ["", "Limitations", *result.warnings]) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--meeting-date", type=date.fromisoformat)
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output directory already exists. Choose a new path.")
        transcript = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
        generator, model = None, args.model or DEFAULT_MODEL
        if any(s.text.strip() for s in transcript.segments):
            settings = settings_from_environment(args.environment_root, args.model)
            model = settings.model
            generator = DecisionReviewGenerator(
                GeminiGenerator(
                    settings,
                    schema=GeneratedDecisions,
                    instruction=INSTRUCTION,
                    max_output_tokens=16384,
                )
            )
        result = track_decisions(transcript, model, generator, args.meeting_date)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "decisions.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        (args.output / "decisions.txt").write_text(render_text(result), encoding="utf-8")
        print(f"Saved {len(result.topics)} topics to {args.output}")
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
