import pytest


@pytest.mark.parametrize("phrase", ["I'm", "I’m", "I am"])
def test_present_first_person_commitment_resolves_owner(phrase):
    from test_day04 import ref, transcript

    from meeting_intelligence.action_extraction import resolve_owner
    from meeting_intelligence.action_schemas import GeneratedOwner

    owner = resolve_owner(
        GeneratedOwner(kind="self", mention=phrase, evidence=ref()),
        transcript(f"{phrase} going to write the notes.", "SPEAKER_00"),
    )
    assert owner.kind == "self" and owner.speaker_id == "SPEAKER_00"
    assert owner.responsible_person is None


def test_invalid_owner_after_correction_preserves_tasks_without_guessing():
    from test_day04 import Stub, generated, transcript

    from meeting_intelligence.action_extraction import extract_actions

    value = generated()
    value["action_items"][0]["owner"]["mention"] = "Invented person"
    stub = Stub(value)
    result = extract_actions(transcript(), "test", stub)
    assert stub.calls == 2
    assert len(result.action_items) == 1
    assert result.action_items[0].owner.kind == "unknown"
    assert result.action_items[0].owner.responsible_person is None
    assert result.action_items[0].owner.evidence == []
    assert any("unverified" in w for w in result.warnings)


def test_owner_fallback_does_not_accept_invented_segment_ids():
    from test_day04 import Stub, generated, transcript

    from meeting_intelligence.action_extraction import extract_actions
    from meeting_intelligence.summarization import SummaryError

    value = generated()
    value["action_items"][0]["owner"]["evidence"] = [{"segment_id": "missing"}]
    with pytest.raises(SummaryError, match="unknown transcript segment"):
        extract_actions(transcript(), "test", Stub(value))


@pytest.mark.parametrize(
    "task,quote,deadline,expected",
    [
        ("close the meeting", "I will close the meeting.", None, 0),
        ("close the meeting", "Please close the meeting tomorrow.", "tomorrow", 1),
        ("close the meeting", "I will close the next meeting.", None, 1),
        ("write the meeting notes", "I will write the meeting notes.", None, 1),
        ("take the display out", "What if we take the display out?", None, 0),
        ("take the display out", "Please take the display out.", None, 1),
        ("take material measurements", "We could take material measurements.", None, 1),
        ("change the specification", "Should we change the specification?", None, 0),
        ("change the specification", "I will change the specification.", None, 1),
        ("be careful about the audience", "I'll be careful about the audience.", None, 0),
        (
            "be careful when reviewing the invoice",
            "Please be careful when reviewing the invoice.",
            None,
            1,
        ),
        ("keep the budget in mind", "We should keep the budget in mind.", None, 0),
        (
            "keep the budget in mind when preparing the quote",
            "Please keep the budget in mind when preparing the quote.",
            None,
            1,
        ),
    ],
)
def test_followup_tasks_distinguished_from_choices_and_meeting_conduct(
    task, quote, deadline, expected
):
    from test_day04 import Stub, generated, transcript

    from meeting_intelligence.action_extraction import extract_actions

    value = generated()
    a = value["action_items"][0]
    a.update(
        task=task,
        owner=dict(kind="unknown", mention=None, evidence=[]),
        deadline=dict(text=deadline, evidence=[{"segment_id": "s0"}] if deadline else []),
    )
    result = extract_actions(transcript(quote), "test", Stub(value))
    assert len(result.action_items) == expected


@pytest.mark.parametrize("value", [0, -1, True, 2.5, "5"])
def test_invalid_beam_setting_fails_before_loading_audio(tmp_path, value):
    from meeting_intelligence.pipeline import transcribe

    with pytest.raises(ValueError, match="Beam size"):
        transcribe(tmp_path / "absent.wav", tmp_path, beam_size=value)


def test_cli_passes_explicit_beam_setting(tmp_path, monkeypatch):
    from test_day03 import transcript

    from meeting_intelligence import __main__ as cli

    captured = {}

    def fake(*args, **kwargs):
        captured.update(kwargs)
        return transcript()

    monkeypatch.setattr(cli, "transcribe", fake)
    monkeypatch.setattr(
        "sys.argv",
        [
            "meeting",
            "source.wav",
            "--environment-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "new"),
            "--beam-size",
            "5",
        ],
    )
    assert cli.main() == 0 and captured["beam_size"] == 5
