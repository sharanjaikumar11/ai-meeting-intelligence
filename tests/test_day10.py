import pytest


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
