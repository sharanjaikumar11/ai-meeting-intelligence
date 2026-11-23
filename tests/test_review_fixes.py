import json

import pytest
from test_day03 import notes, transcript

from meeting_intelligence.pipeline import crop_turns
from meeting_intelligence.schemas import Turn
from meeting_intelligence.summarization import (
    Generation,
    SummaryError,
    guard_summary_claims,
    summarize,
)
from meeting_intelligence.summary_schemas import GeneratedNotes


def test_context_crop_preserves_relative_timestamps_and_excludes_outside_turns():
    turns = [
        Turn(start=1, end=3, speaker_id="A"),
        Turn(start=8, end=12, speaker_id="B"),
        Turn(start=15, end=25, speaker_id="C"),
        Turn(start=30, end=40, speaker_id="D"),
    ]
    result = crop_turns(turns, 10, 10)
    assert [(t.start, t.end, t.speaker_id) for t in result] == [(0, 2, "B"), (5, 10, "C")]
    assert turns[1].start == 8


def test_review_uses_source_and_candidate_and_revalidates_citations():
    class Reviewer:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            value = notes()
            if self.calls == 2:
                request = json.loads(payload)
                assert request["transcript"]["segments"][0]["text"] == transcript().segments[0].text
                assert request["candidate"]["summary"]
                value["summary"][0]["evidence"][0]["segment_id"] = "invented"
            return Generation(json.dumps(value))

    with pytest.raises(SummaryError, match="unknown transcript segment"):
        summarize(transcript(), "test", Reviewer())


def test_guards_remove_bad_roles_and_duration_from_all_generated_fields():
    value = notes()
    reference = [{"segment_id": "seg_00000"}]
    value["summary"].append({"text": "The meeting lasts 25 minutes.", "evidence": reference})
    value["key_discussion_points"] = [
        {"topic": "Meeting Duration", "detail": "Planned for 25 minutes.", "evidence": reference},
        {
            "topic": "Introductions",
            "detail": "One person is a huge interface.",
            "evidence": reference,
        },
    ]
    source = transcript("We will do this over the next 25 minutes. I'm a huge interface.")
    result, warnings = guard_summary_claims(GeneratedNotes.model_validate(value), source)
    assert len(result.summary) == 1 and not result.key_discussion_points
    assert len(warnings) == 2


def test_explicit_agenda_window_is_preserved():
    value = notes()
    value["summary"][0]["text"] = "The planned agenda covers the next 25 minutes."
    result, warnings = guard_summary_claims(
        GeneratedNotes.model_validate(value), transcript("Our work over the next 25 minutes.")
    )
    assert result.summary[0].text == value["summary"][0]["text"]
    assert not warnings


def test_actual_explicit_meeting_duration_is_not_suppressed():
    value = notes()
    value["summary"][0]["text"] = "The meeting will last 25 minutes."
    result, warnings = guard_summary_claims(
        GeneratedNotes.model_validate(value), transcript("The meeting will last 25 minutes.")
    )
    assert result.summary and not warnings


def test_guard_rejects_when_no_safe_summary_remains():
    value = notes()
    value["summary"][0]["text"] = "A huge interface joined."
    with pytest.raises(SummaryError, match="No summary statements"):
        guard_summary_claims(
            GeneratedNotes.model_validate(value), transcript("I'm a huge interface.")
        )


def test_decision_review_receives_original_turns_and_accounts_for_both_calls():
    from meeting_intelligence.decision_tracking import DecisionReviewGenerator

    class Reviewer:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            if self.calls == 2:
                request = json.loads(payload)
                assert request["source_request"]["segments"][0]["text"] == "We will try Monday."
                assert request["candidate"] == '{"topics": []}'
            return Generation('{"topics": []}', "test", {"total_token_count": 10})

    generator = Reviewer()
    response = DecisionReviewGenerator(generator).generate(
        json.dumps({"segments": [{"text": "We will try Monday."}]})
    )
    assert generator.calls == 2
    assert response.usage["total_token_count"] == 20


def test_daily_quota_error_is_specific_without_leaking_server_details(monkeypatch):
    from test_day03 import install_fake_client

    from meeting_intelligence.summarization import GeminiGenerator, Settings

    class DailyQuota(Exception):
        code = 429
        details = {
            "error": {
                "message": "secret request details",
                "details": [
                    {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}]}
                ],
            }
        }

    install_fake_client(monkeypatch, error=DailyQuota())
    with pytest.raises(SummaryError, match="daily quota") as caught:
        GeminiGenerator(Settings("test-secret")).generate("{}")
    assert "secret" not in str(caught.value)
