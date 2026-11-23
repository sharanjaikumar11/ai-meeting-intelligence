import json
from datetime import date

import pytest
from pydantic import ValidationError

from meeting_intelligence.action_extraction import (
    extract_actions,
    resolve_deadline,
    resolve_owner,
)
from meeting_intelligence.action_schemas import GeneratedActions, GeneratedDeadline, GeneratedOwner
from meeting_intelligence.extract_actions import main, render_text
from meeting_intelligence.schemas import Segment, Speaker, Transcript
from meeting_intelligence.summarization import Generation, SummaryError


def transcript(text="Alice, prepare the report by tomorrow.", speaker=None):
    return Transcript(
        source_file="synthetic-test-fixture",
        source_duration_seconds=60,
        processed_start_seconds=0,
        processed_duration_seconds=60,
        language="en",
        asr_model="synthetic",
        diarization_model="synthetic" if speaker else None,
        diarization_status="completed" if speaker else "skipped",
        text=text,
        speakers=[Speaker(id=speaker)] if speaker else [],
        segments=[
            Segment(
                id="s0", source_segment_id="raw0", start=10, end=20, text=text, speaker_id=speaker
            )
        ]
        if text
        else [],
        diarization_turns=[],
        exclusive_diarization_turns=[],
    )


def ref(segment="s0"):
    return [{"segment_id": segment}]


def generated():
    return {
        "action_items": [
            {
                "task": "Prepare the report.",
                "assignment_type": "assignment",
                "evidence": ref(),
                "owner": {"kind": "person", "mention": "Alice", "evidence": ref()},
                "deadline": {"text": "tomorrow", "evidence": ref()},
            }
        ],
        "pending_questions": [],
    }


class Stub:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def generate(self, payload):
        self.calls += 1
        return Generation(json.dumps(self.value), "test-model")


def test_action_owner_deadline_and_evidence():
    result = extract_actions(transcript(), "test", Stub(generated()), date(2026, 11, 15))
    action = result.action_items[0]
    assert action.owner.responsible_person == "Alice"
    assert action.deadline.date_iso == date(2026, 11, 16)
    assert action.deadline.resolution == "relative_date"
    assert action.evidence[0].quote == transcript().segments[0].text
    assert action.evidence[0].start == 10
    assert "Alice (person)" in render_text(result)


def test_relative_deadline_never_uses_current_date():
    result = extract_actions(transcript(), "test", Stub(generated()))
    assert result.action_items[0].deadline.date_iso is None
    assert result.action_items[0].deadline.text == "tomorrow"
    assert result.action_items[0].deadline.resolution == "unresolved"


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("2026-12-01", date(2026, 12, 1)),
        ("by 2026-12-01", date(2026, 12, 1)),
        ("today", date(2026, 11, 15)),
        ("in 3 days", date(2026, 11, 18)),
    ],
)
def test_supported_date_forms(phrase, expected):
    d = GeneratedDeadline(text=phrase, evidence=ref())
    result = resolve_deadline(d, transcript("Finish it " + phrase + "."), date(2026, 11, 15))
    assert result.date_iso == expected


@pytest.mark.parametrize(
    "phrase", ["next Friday", "before the next meeting", "2026-02-30", "11/12", "tomorrow at five"]
)
def test_ambiguous_or_invalid_dates_preserved(phrase):
    d = GeneratedDeadline(text=phrase, evidence=ref())
    result = resolve_deadline(d, transcript("Finish it " + phrase + "."), date(2026, 11, 15))
    assert result.date_iso is None
    assert result.text == phrase
    assert result.resolution == "unresolved"


def test_unknown_owner_and_missing_deadline_are_null():
    value = generated()
    value["action_items"][0]["owner"] = {"kind": "unknown", "mention": None, "evidence": []}
    value["action_items"][0]["deadline"] = {"text": None, "evidence": []}
    result = extract_actions(transcript("We should prepare a report."), "test", Stub(value))
    assert result.action_items[0].owner.responsible_person is None
    assert result.action_items[0].deadline.resolution == "missing"


def test_role_is_not_converted_to_person():
    owner = GeneratedOwner(kind="role", mention="industrial designer", evidence=ref())
    resolved = resolve_owner(owner, transcript("The industrial designer will prepare a sketch."))
    assert resolved.mention == "industrial designer"
    assert resolved.responsible_person is None


def test_self_owner_uses_speaker_not_inferred_name():
    owner = GeneratedOwner(kind="self", mention="I'll", evidence=ref())
    result = resolve_owner(owner, transcript("I'll send the report.", "SPEAKER_00"))
    assert result.speaker_id == "SPEAKER_00"
    assert result.responsible_person is None


def test_self_owner_name_only_from_confirmed_mapping():
    source = transcript("I'll send it.", "SPEAKER_00")
    source.speakers[0].name = "Alice"
    source.speakers[0].name_source = "user_provided"
    result = resolve_owner(GeneratedOwner(kind="self", mention="I'll", evidence=ref()), source)
    assert result.responsible_person == "Alice"


def test_self_owner_without_speaker_remains_unresolved():
    result = resolve_owner(
        GeneratedOwner(kind="self", mention="I", evidence=ref()), transcript("I will send it.")
    )
    assert result.speaker_id is None and result.responsible_person is None


def test_unknown_owner_cannot_have_invented_mention():
    with pytest.raises(ValidationError):
        GeneratedOwner(kind="unknown", mention="Alice", evidence=[])


def test_owner_cannot_match_substring_of_unrelated_word():
    with pytest.raises(SummaryError, match="exact phrase"):
        resolve_owner(
            GeneratedOwner(kind="person", mention="Ann", evidence=ref()),
            transcript("Annex preparation is needed."),
        )


def test_pronoun_cannot_be_a_person_name():
    with pytest.raises(SummaryError, match="pronoun"):
        resolve_owner(
            GeneratedOwner(kind="person", mention="you", evidence=ref()),
            transcript("Could you do it?"),
        )


def test_invented_deadline_rejected():
    with pytest.raises(SummaryError, match="Deadline phrase"):
        resolve_deadline(
            GeneratedDeadline(text="tomorrow", evidence=ref()),
            transcript("Prepare the report."),
            date(2026, 11, 15),
        )


def test_invented_evidence_rejected():
    value = generated()
    value["action_items"][0]["evidence"] = ref("made-up")
    with pytest.raises(SummaryError, match="unknown transcript segment"):
        extract_actions(transcript(), "test", Stub(value))


def test_pending_question_is_scoped_to_supplied_transcript():
    value = {
        "action_items": [],
        "pending_questions": [
            {"question": "Which hosting region should be used?", "evidence": ref()}
        ],
    }
    result = extract_actions(
        transcript("Which hosting region should we use? We will decide next meeting."),
        "test",
        Stub(value),
    )
    assert result.pending_questions[0].status == "unresolved_in_supplied_transcript"
    assert result.pending_questions[0].evidence[0].start == 10


def test_generated_dates_are_not_accepted():
    value = generated()
    value["action_items"][0]["deadline"]["date_iso"] = "2030-01-01"
    with pytest.raises(SummaryError, match="schema"):
        extract_actions(transcript(), "test", Stub(value))


def test_empty_transcript_and_empty_extraction():
    stub = Stub(generated())
    assert extract_actions(transcript(""), "test", stub).generation_status == "no_speech"
    assert stub.calls == 0
    result = extract_actions(
        transcript("Hello everyone."), "test", Stub({"action_items": [], "pending_questions": []})
    )
    assert result.action_items == [] and result.pending_questions == []


def test_cli_preserves_existing_output(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "sys.argv",
        [
            "extract_actions",
            "missing.json",
            "--environment-root",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 1


def test_day04_sdk_uses_action_schema_and_prompt(monkeypatch):
    from types import SimpleNamespace

    from google import genai

    from meeting_intelligence.action_extraction import ACTION_INSTRUCTION
    from meeting_intelligence.summarization import GeminiGenerator, Settings

    captured = {}

    class Client:
        def __init__(self, **kwargs):
            self.models = self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                candidates=[SimpleNamespace(finish_reason="STOP")],
                text=json.dumps(generated()),
                model_version="test",
                usage_metadata=None,
            )

    monkeypatch.setattr(genai, "Client", Client)
    GeminiGenerator(
        Settings("test"), schema=GeneratedActions, instruction=ACTION_INSTRUCTION
    ).generate("{}")
    assert "action_items" in captured["config"].response_json_schema["properties"]
    assert captured["config"].system_instruction == ACTION_INSTRUCTION
    assert "summary" not in captured["config"].response_json_schema["properties"]
