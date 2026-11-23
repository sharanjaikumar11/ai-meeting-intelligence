import json
from pathlib import Path

import pytest

from meeting_intelligence.summarization import Generation, Settings, SummaryError
from meeting_intelligence.summary_schemas import GeneratedNotes


def module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    import complete_day08_budgeted

    return complete_day08_budgeted


def test_budget_cache_and_persistence(monkeypatch, tmp_path):
    m = module(monkeypatch)
    calls = []

    class Fake:
        def __init__(self, *args, **kwargs):
            assert kwargs["retry_attempts"] == 1

        def generate(self, payload):
            calls.append(payload)
            return Generation("{}", "test", {})

    monkeypatch.setattr(m, "GeminiGenerator", Fake)
    b = m.Budget(tmp_path, 1)
    g = b.generator(Settings("not-a-real-key"), GeneratedNotes, "test")
    assert g.generate("one").text == "{}"
    assert g.generate("one").text == "{}" and len(calls) == 1
    resumed = m.Budget(tmp_path, 1).generator(Settings("not-a-real-key"), GeneratedNotes, "test")
    assert resumed.generate("one").text == "{}"
    with pytest.raises(SummaryError, match="budget"):
        resumed.generate("two")
    assert len(calls) == 1


def test_failed_attempt_consumes_budget(monkeypatch, tmp_path):
    m = module(monkeypatch)

    class Fake:
        def __init__(self, *args, **kwargs):
            pass

        def generate(self, payload):
            raise SummaryError("Gemini daily quota reached.")

    monkeypatch.setattr(m, "GeminiGenerator", Fake)
    g = m.Budget(tmp_path, 1).generator(Settings("not-a-real-key"), GeneratedNotes, "test")
    with pytest.raises(SummaryError, match="daily quota"):
        g.generate("one")
    with pytest.raises(SummaryError, match="budget"):
        g.generate("one")
    assert json.loads((tmp_path / "request_ledger.json").read_text())[0]["status"] == "failed"


def test_batch_answers_validate_each_question(monkeypatch, tmp_path):
    m = module(monkeypatch)
    from test_day03 import transcript

    responses = {
        "answers": [
            {"question_index": 1, "status": "not_found", "claims": [], "limitation": "Not stated."},
            {
                "question_index": 0,
                "status": "answered",
                "claims": [
                    {
                        "text": "A remote control was discussed.",
                        "evidence": [{"segment_id": "seg_00000"}],
                    }
                ],
                "limitation": None,
            },
        ]
    }

    class Fake:
        def generate(self, payload):
            return Generation(json.dumps(responses), "test", {"total_token_count": 5})

    class Budget:
        def generator(self, *args):
            return Fake()

    result = m.questions(
        transcript(),
        ["What was discussed?", "What account number?"],
        Settings("not-a-real-key"),
        Budget(),
    )
    assert result["answers"][0]["question"] == "What was discussed?"
    assert result["answers"][1]["status"] == "not_found"
    assert (
        result["answers"][0]["claims"][0]["evidence"][0]["quote"] == transcript().segments[0].text
    )
    assert result["usage"]["total_token_count"] == 10


def test_action_correction_preserves_usage_and_validates_again():
    from test_day04 import generated, transcript

    from meeting_intelligence.action_extraction import extract_actions

    class Fake:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            if self.calls == 2:
                assert "invalid_candidate" in json.loads(payload)
            return Generation(
                json.dumps({} if self.calls == 1 else generated()), "test", {"total_token_count": 4}
            )

    f = Fake()
    result = extract_actions(transcript(), "test", f)
    assert f.calls == 2 and result.action_items[0].owner.responsible_person == "Alice"
    assert result.usage["total_token_count"] == 8


def test_action_correction_stops_after_two_invalid_responses():
    from test_day04 import transcript

    from meeting_intelligence.action_extraction import extract_actions

    class Fake:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            return Generation("{}", "test")

    f = Fake()
    with pytest.raises(SummaryError):
        extract_actions(transcript(), "test", f)
    assert f.calls == 2


@pytest.mark.parametrize("stated,expected", [("25", 0), ("12", 1)])
def test_monetary_claim_needs_its_number_in_evidence(stated, expected):
    from test_day05 import Stub, event, source

    from meeting_intelligence.decision_tracking import track_decisions

    e = event(0, "recalled")
    e["statement"] = "The cost is " + stated + " euros."
    stub = Stub([e])
    stub.value["topics"][0]["topic"] = "Production cost"
    r = track_decisions(source(["Remember the cost is 12 euros."]), "test", stub)
    assert len(r.topics) == expected
    if not expected:
        assert any("omitted" in w for w in r.warnings)


@pytest.mark.parametrize(
    "quote,expected", [("Yeah.", "not_found"), ("I will write the report.", "answered")]
)
def test_anonymous_owner_needs_explicit_commitment(quote, expected):
    from test_day04 import transcript

    from meeting_intelligence.qa import ask

    t = transcript(quote, speaker="SPEAKER_00")

    class Fake:
        def generate(self, payload):
            return Generation(
                json.dumps(
                    {
                        "status": "answered",
                        "claims": [
                            {
                                "text": "SPEAKER_00 was assigned to write the report.",
                                "evidence": [{"segment_id": "s0"}],
                            }
                        ],
                        "limitation": None,
                    }
                ),
                "test",
            )

    answer = ask(t, "Who writes the report?", "test", Fake())
    assert answer.status == expected
    if expected == "not_found":
        assert not answer.claims and answer.limitation


def test_severely_uncertain_transcript_stops_before_model():
    from test_day03 import transcript

    from meeting_intelligence.schemas import Word
    from meeting_intelligence.summarization import build_payload

    t = transcript()
    t.segments[0].words = [Word(start=65, end=66, text="word", probability=0.1) for _ in range(10)]
    with pytest.raises(SummaryError, match="no transcript was sent"):
        build_payload(t)


def test_withdrawing_explicit_alternative_proposal_keeps_agreement():
    from test_day05 import Stub, event, source

    from meeting_intelligence.decision_tracking import track_decisions

    events = [event(0, "agreed"), event(1, "proposed"), event(2, "withdrawn", [1])]
    events[2]["statement"] = "The proposal for the alternative is withdrawn."
    topic = track_decisions(
        source(["Agreed wheel.", "Maybe a ball?", "Withdraw that proposal; wheel is better."]),
        "test",
        Stub(events),
    ).topics[0]
    assert topic.status == "agreed" and topic.final_agreed_event_id == topic.events[0].id
    assert not topic.unresolved_event_ids


@pytest.mark.parametrize(
    "quote,expected",
    [("We could have a yellow color.", 0), ("Please offer a yellow color option.", 1)],
)
def test_product_configuration_is_not_implicitly_a_task(quote, expected):
    from test_day04 import Stub, generated, transcript

    from meeting_intelligence.action_extraction import extract_actions

    value = generated()
    item = value["action_items"][0]
    item.update(
        task="Offer a yellow color",
        owner={"kind": "unknown", "mention": None, "evidence": []},
        deadline={"text": None, "evidence": []},
    )
    result = extract_actions(transcript(quote), "test", Stub(value))
    assert len(result.action_items) == expected
