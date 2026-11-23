"""Verify a saved QA answer's source fingerprint and copied evidence."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.qa import Answer
from meeting_intelligence.schemas import Transcript


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("transcript", type=Path)
    p.add_argument("answer", type=Path)
    a = p.parse_args()
    t = Transcript.model_validate_json(a.transcript.read_text(encoding="utf-8"))
    answer = Answer.model_validate_json(a.answer.read_text(encoding="utf-8"))
    assert (
        answer.source_transcript_sha256 == hashlib.sha256(t.model_dump_json().encode()).hexdigest()
    )
    lookup = {s.id: s for s in t.segments}
    count = 0
    for claim in answer.claims:
        for ref in claim.evidence:
            s = lookup[ref.segment_id]
            assert (ref.quote, ref.start, ref.end, ref.speaker_id) == (
                s.text,
                s.start,
                s.end,
                s.speaker_id,
            )
            count += 1
    print(
        json.dumps(
            {
                "status": answer.status,
                "verified_evidence_references": count,
                "fingerprint_verified": True,
            }
        )
    )


if __name__ == "__main__":
    main()
