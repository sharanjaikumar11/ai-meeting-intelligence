"""Check saved summary provenance and the known role/duration regression cases."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summary_schemas import MeetingSummary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("transcript", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--known-regressions", action="store_true")
    args = parser.parse_args()
    source = Transcript.model_validate_json(args.transcript.read_text(encoding="utf-8"))
    summary = MeetingSummary.model_validate_json(args.summary.read_text(encoding="utf-8"))
    assert (
        summary.source_transcript_sha256
        == hashlib.sha256(source.model_dump_json().encode()).hexdigest()
    )
    segments = {s.id: s for s in source.segments}
    count = 0
    for item in summary.summary_statements + summary.key_discussion_points:
        for ref in item.evidence:
            segment = segments[ref.segment_id]
            assert (ref.quote, ref.start, ref.end, ref.speaker_id) == (
                segment.text,
                segment.start,
                segment.end,
                segment.speaker_id,
            )
            count += 1
    if args.known_regressions:
        claims = [s.text for s in summary.summary_statements] + [
            p.topic + ": " + p.detail for p in summary.key_discussion_points
        ]
        assert all("huge interface" not in c.lower() for c in claims)
        assert all("agenda" in c.lower() for c in claims if "25" in c or "twenty five" in c.lower())
        assert all("meeting duration" not in c.lower() for c in claims)
    print(
        json.dumps(
            {
                "schema_and_fingerprint": "passed",
                "evidence_references_verified": count,
                "known_regressions_checked": args.known_regressions,
                "summary_statements": len(summary.summary_statements),
                "discussion_points": len(summary.key_discussion_points),
            }
        )
    )


if __name__ == "__main__":
    main()
