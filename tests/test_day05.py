import json
from datetime import date

import pytest

from meeting_intelligence.decision_tracking import track_decisions
from meeting_intelligence.schemas import Segment, Transcript
from meeting_intelligence.summarization import Generation, SummaryError


def source(lines):
    return Transcript(
        source_file="synthetic",
        source_duration_seconds=100,
        processed_start_seconds=0,
        processed_duration_seconds=100,
        language="en",
        asr_model="synthetic",
        diarization_model=None,
        diarization_status="skipped",
        text=" ".join(lines),
        speakers=[],
        segments=[
            Segment(id=f"s{i}", source_segment_id=f"s{i}", start=i * 5, end=i * 5 + 4, text=t)
            for i, t in enumerate(lines)
        ],
        diarization_turns=[],
        exclusive_diarization_turns=[],
    )


def event(i, kind, resolves=None, deadline=None):
    return dict(
        type=kind,
        statement=f"Outcome {i}",
        anchor_segment_id=f"s{i}",
        evidence=[{"segment_id": f"s{i}"}],
        deadline_text=deadline,
        resolves=resolves or [],
    )


class Stub:
    def __init__(self, events, kind="decision"):
        self.value = {"topics": [{"topic": "Launch", "kind": kind, "events": events}]}

    def generate(self, payload):
        return Generation(json.dumps(self.value), "test")


def test_accepted_change_preserves_history():
    result = track_decisions(
        source(["Use A.", "Agreed A.", "Try B.", "Agreed B."]),
        "test",
        Stub(
            [
                event(0, "proposed"),
                event(1, "agreed", [0]),
                event(2, "proposed"),
                event(3, "agreed", [2]),
            ]
        ),
    ).topics[0]
    assert result.final_agreed_decision == "Outcome 3"
    assert result.events[3].supersedes == result.events[1].id
    assert result.unresolved_event_ids == []


def test_proposal_does_not_replace_agreement():
    result = track_decisions(
        source(["Agreed A.", "Maybe B?"]), "test", Stub([event(0, "agreed"), event(1, "proposed")])
    ).topics[0]
    assert result.final_agreed_decision == "Outcome 0"
    assert result.unresolved_event_ids == [result.events[1].id]


@pytest.mark.parametrize("kind", ["disagreed", "reopened", "deferred"])
def test_open_issue_prevents_claim_of_final_agreement(kind):
    result = track_decisions(
        source(["Agreed A.", "Issue remains."]), "test", Stub([event(0, "agreed"), event(1, kind)])
    ).topics[0]
    assert result.status == "unresolved"
    assert result.final_agreed_decision is None
    assert result.last_agreed_event_id == result.events[0].id


def test_explicit_resolution_clears_disagreement():
    result = track_decisions(
        source(["A.", "I object.", "Resolved; agreed B."]),
        "test",
        Stub([event(0, "agreed"), event(1, "disagreed"), event(2, "agreed", [1])]),
    ).topics[0]
    assert result.status == "agreed"
    assert result.disagreement_event_ids == [result.events[1].id]


def test_deadline_replacement_and_normalization():
    result = track_decisions(
        source(["By 2026-04-06.", "Agreed tomorrow."]),
        "test",
        Stub(
            [event(0, "agreed", deadline="2026-04-06"), event(1, "agreed", deadline="tomorrow")],
            "deadline",
        ),
        date(2026, 4, 1),
    ).topics[0]
    assert result.final_deadline.date_iso == date(2026, 4, 2)
    assert result.events[0].deadline.date_iso == date(2026, 4, 6)


@pytest.mark.parametrize(
    "events",
    [
        [event(1, "agreed"), event(0, "agreed")],
        [event(0, "agreed", [1])],
        [event(0, "agreed"), event(1, "agreed", [0])],
        [event(0, "proposed"), event(1, "disagreed", [0])],
    ],
)
def test_invalid_chronology_or_resolution_rejected(events):
    with pytest.raises(SummaryError):
        track_decisions(source(["A", "B"]), "test", Stub(events))


def test_withdrawal_retains_history_without_final():
    result = track_decisions(
        source(["Agreed A.", "Cancel A."]),
        "test",
        Stub([event(0, "agreed"), event(1, "withdrawn")]),
    ).topics[0]
    assert result.status == "withdrawn" and result.final_agreed_event_id is None


def test_empty_no_api():
    assert track_decisions(source([]), "test").generation_status == "no_speech"


def test_deadline_phrase_must_be_in_source():
    with pytest.raises(SummaryError):
        track_decisions(
            source(["No date."]),
            "test",
            Stub([event(0, "agreed", deadline="tomorrow")], "deadline"),
        )


def test_unknown_or_uncited_anchor_rejected():
    item = event(0, "agreed")
    item["anchor_segment_id"] = "unknown"
    with pytest.raises(SummaryError):
        track_decisions(source(["Agreed A."]), "test", Stub([item]))


def test_one_bounded_correction_then_valid_result():
    class Correcting:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            if self.calls == 2:
                assert "validation_error" in json.loads(payload)
            return Stub([event(0, "agreed", [1] if self.calls == 1 else [])]).generate(payload)

    generator = Correcting()
    result = track_decisions(source(["Agreed A."]), "test", generator)
    assert generator.calls == 2 and result.topics[0].status == "agreed"
    assert any("correction" in warning for warning in result.warnings)


def test_invalid_correction_stops_after_two_calls():
    class Invalid:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            return Stub([event(0, "agreed", [1])]).generate(payload)

    generator = Invalid()
    with pytest.raises(SummaryError):
        track_decisions(source(["Agreed A."]), "test", generator)
    assert generator.calls == 2


def test_cli_preserves_existing_output(tmp_path, monkeypatch):
    from meeting_intelligence.track_decisions import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "track_decisions",
            "missing.json",
            "--environment-root",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 1


def test_topics_have_independent_histories():
    class Multiple:
        def generate(self, payload):
            return Generation(
                json.dumps(
                    {
                        "topics": [
                            {"topic": "A", "kind": "decision", "events": [event(0, "agreed")]},
                            {"topic": "B", "kind": "decision", "events": [event(1, "deferred")]},
                        ]
                    }
                )
            )

    result = track_decisions(source(["Agreed A.", "Defer B."]), "test", Multiple())
    assert result.topics[0].status == "agreed"
    assert result.topics[1].status == "unresolved"


def test_recalled_deadline_is_retained_and_replaced():
    result = track_decisions(
        source(["We had the deadline last Friday.", "Agreed, try Monday."]),
        "test",
        Stub(
            [event(0, "recalled", deadline="last Friday"), event(1, "agreed", deadline="Monday")],
            "deadline",
        ),
    ).topics[0]
    assert result.events[1].supersedes == result.events[0].id
    assert result.final_deadline.text == "Monday"
    assert result.events[0].deadline.text == "last Friday"


def test_later_recollection_cannot_overwrite_new_agreement():
    result = track_decisions(
        source(["Agreed Monday.", "We used to plan Friday."]),
        "test",
        Stub(
            [event(0, "agreed", deadline="Monday"), event(1, "recalled", deadline="Friday")],
            "deadline",
        ),
    ).topics[0]
    assert result.final_deadline.text == "Monday"


def test_recollection_cannot_restore_withdrawn_agreement():
    result = track_decisions(
        source(["Cancel the plan.", "The old plan was A."]),
        "test",
        Stub([event(0, "withdrawn"), event(1, "recalled")]),
    ).topics[0]
    assert result.final_agreed_decision is None
