"""Apply explicit reviewed speaker intervals without overwriting automatic output."""

import argparse
import hashlib
import json
from pathlib import Path

from .alignment import align_segments
from .schemas import Transcript, Turn


def apply_corrections(transcript, corrections):
    turns = list(transcript.exclusive_diarization_turns)
    known = {s.id for s in transcript.speakers}
    lower = transcript.processed_start_seconds
    upper = lower + transcript.processed_duration_seconds
    previous_end = lower
    for correction in corrections:
        patch = Turn.model_validate({k: correction[k] for k in ("start", "end", "speaker_id")})
        if (
            patch.speaker_id not in known
            or patch.start < previous_end
            or patch.end > upper
            or patch.end <= patch.start
        ):
            raise ValueError(
                "Corrections must be ordered, disjoint, inside the excerpt, and use existing speaker IDs."
            )
        if not correction.get("reason"):
            raise ValueError("Every correction requires a review reason.")
        previous_end = patch.end
        revised = []
        for turn in turns:
            if turn.end <= patch.start or turn.start >= patch.end:
                revised.append(turn)
            else:
                if turn.start < patch.start:
                    revised.append(turn.model_copy(update={"end": patch.start}))
                if turn.end > patch.end:
                    revised.append(turn.model_copy(update={"start": patch.end}))
        turns = sorted(revised + [patch], key=lambda t: (t.start, t.end))
    raw = []
    for segment in transcript.segments:
        raw.append(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [
                    {"start": w.start, "end": w.end, "word": w.text, "probability": w.probability}
                    for w in segment.words
                ],
            }
        )
    segments = align_segments(
        raw,
        turns,
        transcript.diarization_turns,
        transcript.source_duration_seconds,
        names={s.id: s.name for s in transcript.speakers if s.name},
    )
    result = transcript.model_copy(
        update={
            "exclusive_diarization_turns": turns,
            "segments": segments,
            "warnings": transcript.warnings
            + [
                "Speaker intervals contain explicit human-reference-assisted corrections. This is a reviewed artifact, not raw automatic diarization or an independent accuracy evaluation."
            ],
        }
    )
    return Transcript.model_validate_json(result.model_dump_json())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("corrections", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Choose a new output directory.")
    source = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
    audit = json.loads(args.corrections.read_text(encoding="utf-8"))
    fingerprint = hashlib.sha256(source.model_dump_json().encode()).hexdigest()
    if audit["source_transcript_sha256"] != fingerprint:
        raise ValueError("Correction source fingerprint mismatch.")
    result = apply_corrections(source, audit["corrections"])
    args.output.mkdir(parents=True)
    (args.output / "transcript.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (args.output / "corrections.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (args.output / "transcript.txt").write_text(
        "\n".join(
            f"[{s.start:.3f}-{s.end:.3f}] {s.speaker_id or 'UNASSIGNED'}: {s.text}"
            for s in result.segments
        ),
        encoding="utf-8",
    )
    print("Saved reviewed transcript and correction audit.")


if __name__ == "__main__":
    main()
