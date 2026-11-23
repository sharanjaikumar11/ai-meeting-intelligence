"""Check saved Day 5 evidence and optionally the authored development fixture outcomes."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.decision_tracking import MeetingDecisions
from meeting_intelligence.schemas import Transcript


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("--synthetic-expectations", action="store_true")
    args = parser.parse_args()
    transcript = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
    result = MeetingDecisions.model_validate_json(args.decisions.read_text(encoding="utf-8"))
    assert (
        result.source_transcript_sha256
        == hashlib.sha256(transcript.model_dump_json().encode()).hexdigest()
    )
    segments = {s.id: s for s in transcript.segments}
    count = 0
    for topic in result.topics:
        for event in topic.events:
            for ref in event.evidence:
                s = segments[ref.segment_id]
                assert (ref.quote, ref.start, ref.end, ref.speaker_id) == (
                    s.text,
                    s.start,
                    s.end,
                    s.speaker_id,
                )
                count += 1
    if args.synthetic_expectations:
        assert transcript.source_file == "synthetic-day05-not-a-recording"
        deadlines = [t for t in result.topics if t.kind == "deadline"]
        assert len(deadlines) == 1
        d = deadlines[0]
        assert d.status == "agreed" and str(d.final_deadline.date_iso) == "2026-04-08"
        assert any(
            e.deadline and str(e.deadline.date_iso) == "2026-04-06" and e.type == "agreed"
            for e in d.events
        )
        assert any(
            e.deadline and str(e.deadline.date_iso) == "2026-04-10" and e.type == "proposed"
            for e in d.events
        )
        decisions = [t for t in result.topics if t.kind == "decision"]
        assert len(decisions) == 2
        settled = [t for t in decisions if t.status == "agreed"]
        assert len(settled) == 1 and "json" in settled[0].final_agreed_decision.lower()
        assert settled[0].disagreement_event_ids and not settled[0].unresolved_event_ids
        unresolved = [t for t in decisions if t.status == "unresolved"]
        assert len(unresolved) == 1 and unresolved[0].final_agreed_decision is None
        assert unresolved[0].disagreement_event_ids and unresolved[0].unresolved_event_ids
    print(
        json.dumps(
            {
                "topics": len(result.topics),
                "verified_references": count,
                "provenance_verified": True,
                "synthetic_expectations_checked": args.synthetic_expectations,
            }
        )
    )


if __name__ == "__main__":
    main()
