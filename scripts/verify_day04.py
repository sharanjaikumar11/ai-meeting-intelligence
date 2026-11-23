"""Verify saved extraction provenance; this is not a semantic accuracy metric."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.action_schemas import MeetingActions
from meeting_intelligence.schemas import Transcript


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("actions", type=Path)
    args = parser.parse_args()
    transcript = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
    result = MeetingActions.model_validate_json(args.actions.read_text(encoding="utf-8"))
    expected = hashlib.sha256(transcript.model_dump_json().encode()).hexdigest()
    if result.source_transcript_sha256 != expected:
        raise ValueError("Transcript fingerprint mismatch")
    segments = {segment.id: segment for segment in transcript.segments}
    references = []
    for action in result.action_items:
        references.extend(action.evidence + action.owner.evidence + action.deadline.evidence)
    for question in result.pending_questions:
        references.extend(question.evidence)
    for ref in references:
        segment = segments[ref.segment_id]
        if (ref.quote, ref.start, ref.end, ref.speaker_id) != (
            segment.text,
            segment.start,
            segment.end,
            segment.speaker_id,
        ):
            raise ValueError(f"Evidence mismatch: {ref.segment_id}")
    print(
        json.dumps(
            {
                "provenance_verified": True,
                "action_count": len(result.action_items),
                "pending_question_count": len(result.pending_questions),
                "verified_references": len(references),
                "semantic_accuracy_evaluated": False,
            }
        )
    )


if __name__ == "__main__":
    main()
