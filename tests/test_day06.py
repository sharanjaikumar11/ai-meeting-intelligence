import json

import pytest
from test_day03 import transcript

from meeting_intelligence.qa import ask, main, render
from meeting_intelligence.summarization import Generation, SummaryError


class Stub:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def generate(self, payload):
        self.calls.append(json.loads(payload))
        return Generation(json.dumps(self.value), "test")


def value():
    return {
        "status": "answered",
        "claims": [
            {
                "text": "The team discussed a remote control.",
                "evidence": [{"segment_id": "seg_00000"}],
            }
        ],
        "limitation": None,
    }


def test_answer_copies_evidence_and_preserves_scope():
    generator = Stub(value())
    result = ask(transcript(), "What was discussed?", "test", generator)
    assert result.claims[0].evidence[0].quote == transcript().segments[0].text
    assert result.claims[0].evidence[0].start == 65
    assert result.input_scope == "excerpt"
    assert "65.00" in render(result)
    assert "source_file" not in json.dumps(generator.calls)


@pytest.mark.parametrize("question", ["", "   ", "x" * 2001])
def test_invalid_question_rejected_before_model(question):
    stub = Stub(value())
    with pytest.raises(ValueError):
        ask(transcript(), question, "test", stub)
    assert not stub.calls


def test_unknown_evidence_rejected():
    v = value()
    v["claims"][0]["evidence"][0]["segment_id"] = "invented"
    with pytest.raises(SummaryError):
        ask(transcript(), "Who?", "test", Stub(v))


@pytest.mark.parametrize("status", ["partial", "not_found"])
def test_missing_information_requires_explanation(status):
    v = value()
    v["status"] = status
    if status == "not_found":
        v["claims"] = []
    with pytest.raises(SummaryError):
        ask(transcript(), "Who?", "test", Stub(v))


def test_abstention_and_empty_transcript():
    stub = Stub({"status": "not_found", "claims": [], "limitation": "No date is stated."})
    assert ask(transcript(), "What date?", "test", stub).answer == "No date is stated."
    assert ask(transcript(""), "What date?").status == "not_found"


def test_partial_answer_keeps_limitation():
    v = value()
    v.update(status="partial", limitation="No owner is specified.")
    assert "No owner is specified." in render(ask(transcript(), "Task and owner?", "test", Stub(v)))


def test_generated_quotes_rejected():
    v = value()
    v["claims"][0]["evidence"][0]["quote"] = "fabricated"
    with pytest.raises(SummaryError):
        ask(transcript(), "Who?", "test", Stub(v))


def test_interactive_empty_transcript_and_exit(tmp_path, monkeypatch, capsys):
    p = tmp_path / "t.json"
    p.write_text(transcript("").model_dump_json())
    monkeypatch.setattr("sys.argv", ["qa", str(p), "--environment-root", str(tmp_path)])
    entries = iter(["", "What was decided?", "/exit"])
    monkeypatch.setattr("builtins.input", lambda _: next(entries))
    assert main() == 0
    assert "No transcribed speech" in capsys.readouterr().out


def test_existing_output_preserved(tmp_path, monkeypatch):
    p = tmp_path / "saved.json"
    p.write_text("keep")
    monkeypatch.setattr(
        "sys.argv",
        [
            "qa",
            "missing.json",
            "--environment-root",
            str(tmp_path),
            "--question",
            "What?",
            "--output",
            str(p),
        ],
    )
    assert main() == 1 and p.read_text() == "keep"


def test_review_preserves_question_and_sums_usage():
    from meeting_intelligence.qa import QAReviewGenerator

    class Model:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            if self.calls == 2:
                assert json.loads(payload)["source_request"]["question"] == "Who?"
            return Generation(json.dumps(value()), "test", {"total_token_count": 10})

    model = Model()
    response = QAReviewGenerator(model).generate(json.dumps({"question": "Who?", "transcript": {}}))
    assert model.calls == 2 and response.usage["total_token_count"] == 20
