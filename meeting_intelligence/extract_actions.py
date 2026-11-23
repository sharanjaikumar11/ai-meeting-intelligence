"""CLI: extract Day 4 actions from a validated Day 2 transcript."""

import argparse
import sys
from datetime import date
from pathlib import Path

from .__main__ import timestamp
from .action_extraction import ACTION_INSTRUCTION, extract_actions
from .action_schemas import GeneratedActions
from .schemas import Transcript
from .summarization import DEFAULT_MODEL, GeminiGenerator, settings_from_environment


def render_text(result):
    lines = [
        f"Scope: {result.input_scope}",
        f"Interval: {timestamp(result.processed_interval.start)} - {timestamp(result.processed_interval.end)}",
        f"Meeting date: {result.meeting_date or 'not supplied'}",
        "",
        "Action items",
    ]
    if not result.action_items:
        lines.append("No supported action items extracted.")
    for item in result.action_items:
        label = (
            item.owner.responsible_person
            or item.owner.speaker_id
            or item.owner.mention
            or "Unknown"
        )
        lines.extend(
            [
                f"- {item.id}: {item.task}",
                f"  Type: {item.assignment_type}",
                f"  Owner: {label} ({item.owner.kind})",
                f"  Deadline: {item.deadline.text or 'Not specified'}",
                f"  Calendar date: {item.deadline.date_iso or 'Unresolved / not specified'}",
            ]
        )
        if item.owner.resolution_note:
            lines.append(f"  Owner note: {item.owner.resolution_note}")
        if item.deadline.resolution_note:
            lines.append(f"  Deadline note: {item.deadline.resolution_note}")
        references = {
            e.segment_id: e for e in item.evidence + item.owner.evidence + item.deadline.evidence
        }
        for evidence in references.values():
            lines.append(
                f'  [{timestamp(evidence.start)} - {timestamp(evidence.end)}] {evidence.segment_id}: "{evidence.quote}"'
            )
    lines.extend(["", "Pending questions (in supplied transcript)"])
    if not result.pending_questions:
        lines.append("No pending questions extracted.")
    for item in result.pending_questions:
        lines.append(f"- {item.id}: {item.question}")
        for evidence in item.evidence:
            lines.append(
                f'  [{timestamp(evidence.start)} - {timestamp(evidence.end)}] {evidence.segment_id}: "{evidence.quote}"'
            )
    lines.extend(["", "Limitations", *[f"- {warning}" for warning in result.warnings]])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Extract actions, owners, deadlines, and pending questions with Gemini."
    )
    parser.add_argument("transcript", type=Path)
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument(
        "--meeting-date",
        type=date.fromisoformat,
        help="Actual recording date YYYY-MM-DD, never today by default",
    )
    parser.add_argument("--model")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output directory already exists. Choose a new path.")
        transcript = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
        if any(segment.text.strip() for segment in transcript.segments):
            settings = settings_from_environment(args.environment_root, args.model)
            print(f"Extracting actions with {settings.model}", flush=True)
            generator = GeminiGenerator(
                settings, schema=GeneratedActions, instruction=ACTION_INSTRUCTION
            )
            result = extract_actions(transcript, settings.model, generator, args.meeting_date)
        else:
            result = extract_actions(
                transcript, args.model or DEFAULT_MODEL, meeting_date=args.meeting_date
            )
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "actions.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )
        (args.output / "actions.txt").write_text(render_text(result), encoding="utf-8")
        print(
            f"Saved {len(result.action_items)} actions and {len(result.pending_questions)} pending questions to {args.output}"
        )
        return 0
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
