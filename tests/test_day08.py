"""Day 8 regression cases; model-independent checks do not imply model accuracy."""

import pytest
from test_day03 import transcript
from test_day07 import client, wait

from meeting_intelligence.action_extraction import extract_actions
from meeting_intelligence.decision_tracking import track_decisions
from meeting_intelligence.media import MediaInputError
from meeting_intelligence.qa import ask
from meeting_intelligence.summarization import summarize


class NoModelCalls:
    def generate(self, payload):
        raise AssertionError("Empty speech must not call the language model")


def test_empty_speech_abstains_across_all_modules():
    t = transcript("")
    model = NoModelCalls()
    assert summarize(t, "test", model).generation_status == "no_speech"
    assert extract_actions(t, "test", model).action_items == []
    assert track_decisions(t, "test", model).topics == []
    assert ask(t, "What was decided?", "test", model).status == "not_found"


def test_whitespace_question_is_client_validation_error(tmp_path):
    c = client(tmp_path)
    assert (
        c.post("/api/meetings/" + "a" * 32 + "/questions", json={"question": "   "}).status_code
        == 422
    )


@pytest.mark.parametrize(
    "message",
    [
        "Input cannot be decoded as a supported audio/video recording.",
        "The input has no audio stream.",
        "Start offset must be before the end of the recording.",
    ],
)
def test_safe_recording_errors_are_actionable(tmp_path, message):
    def worker(p, s):
        raise MediaInputError(message)

    c = client(tmp_path, worker)
    id = c.post("/api/meetings", files={"recording": ("bad.wav", b"bad")}).json()["id"]
    result = wait(c, id)
    assert result["status"] == "failed" and result["error"] == message
    assert c.get(f"/api/meetings/{id}/download").status_code == 409


def test_unexpected_errors_do_not_expose_local_secrets(tmp_path):
    def worker(p, s):
        raise ValueError("PRIVATE_KEY_EXAMPLE /private/path")

    c = client(tmp_path, worker)
    id = c.post("/api/meetings", files={"recording": ("bad.wav", b"bad")}).json()["id"]
    result = wait(c, id)
    assert result["status"] == "failed" and "PRIVATE_KEY_EXAMPLE" not in result["error"]


def test_later_module_failure_keeps_download_and_retry(tmp_path):
    # Existing Day 7 model-adapter regression covers actual pipeline stage reuse.
    # Here verify interruption handling for a persisted job without a running worker.
    import json
    from uuid import uuid4

    id = uuid4().hex
    path = tmp_path / "outputs/web" / id
    path.mkdir(parents=True)
    (path / "state.json").write_text(
        json.dumps(
            dict(
                id=id,
                name="meeting.wav",
                status="processing",
                stage="Summarizing",
                error=None,
                start=0,
                duration=None,
                diarize=False,
                meeting_date=None,
            )
        )
    )
    (path / "result.json").write_text(json.dumps({"transcript": {"segments": []}}))
    c = client(tmp_path)
    assert c.get("/api/meetings/" + id).json()["status"] == "interrupted"
    assert c.get(f"/api/meetings/{id}/download").status_code == 200
    assert c.post(f"/api/meetings/{id}/retry").status_code == 202
    assert wait(c, id)["status"] == "completed"


def test_same_turn_reaffirmation_resolves_rejected_alternative():
    from test_day05 import Stub, event, source

    t = source(
        [
            "Agreed Friday.",
            "Could we move to Monday?",
            "No Monday; we all confirm Friday remains agreed.",
        ]
    )
    events = [
        event(0, "agreed", deadline="Friday"),
        event(1, "proposed", deadline="Monday"),
        event(2, "disagreed"),
        event(2, "agreed", [1, 2], deadline="Friday"),
    ]
    topic = track_decisions(t, "test", Stub(events, "deadline")).topics[0]
    assert topic.status == "agreed" and topic.final_deadline.text == "Friday"
    assert topic.final_deadline.date_iso is None
    assert topic.unresolved_event_ids == []
    assert len(topic.disagreement_event_ids) == 1


@pytest.mark.parametrize(
    "samples,expected",
    [(b"\x00\x00" * 20, True), (b"\x00\x00" * 19 + b"\x01\x00", False), (b"\xff\xff" * 20, False)],
)
def test_silence_guard_keeps_even_one_quiet_sample(tmp_path, samples, expected):
    import wave

    from meeting_intelligence.media import is_digital_silence

    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(samples)
    assert is_digital_silence(path) is expected


def test_digital_silence_bypasses_models(tmp_path, monkeypatch):
    import wave

    import whisper

    from meeting_intelligence import pipeline

    path = tmp_path / "silence.wav"
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(bytes(32000))
    monkeypatch.setattr(pipeline, "ffmpeg_tools", lambda root: (None, None))
    monkeypatch.setattr(
        pipeline, "probe_media", lambda *args: {"duration": 1, "audio_stream_index": 0}
    )

    def decode(source, destination, *args):
        destination.write_bytes(path.read_bytes())
        return 1

    monkeypatch.setattr(pipeline, "decode", decode)

    def forbidden(*args, **kwargs):
        raise AssertionError("Silent audio must not invoke models or request credentials")

    monkeypatch.setattr(whisper, "load_model", forbidden)
    monkeypatch.setattr(pipeline.diarization, "require_access_token", forbidden)
    t = pipeline.transcribe(path, tmp_path)
    assert t.text == "" and t.segments == [] and t.diarization_status == "skipped"
    assert t.asr_model == "not_run_digital_silence"


@pytest.mark.parametrize(
    "probabilities,expected",
    [([0.1] * 3 + [0.9] * 7, True), ([0.9] * 10, False), ([None] * 10, False)],
)
def test_low_confidence_warning_is_only_a_review_heuristic(probabilities, expected):
    from types import SimpleNamespace

    from meeting_intelligence.pipeline import transcription_quality_warnings

    segments = [SimpleNamespace(words=[SimpleNamespace(probability=p) for p in probabilities])]
    warnings = transcription_quality_warnings(segments)
    assert bool(warnings) is expected
    if warnings:
        assert "not an accuracy score" in warnings[0]


def test_summary_schema_correction_is_bounded_and_counts_usage():
    import json

    from test_day03 import notes

    from meeting_intelligence.summarization import Generation

    class Generator:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            if self.calls == 2:
                assert "validation_errors" in json.loads(payload)
            return Generation(
                json.dumps({} if self.calls == 1 else notes()), "test", {"total_token_count": 5}
            )

    generator = Generator()
    result = summarize(transcript(), "test", generator)
    assert generator.calls == 3 and result.usage["total_token_count"] == 15
    assert any("schema correction" in w for w in result.warnings)


def test_summary_schema_failure_stops_after_one_correction():
    from meeting_intelligence.summarization import Generation, SummaryError

    class Generator:
        calls = 0

        def generate(self, payload):
            self.calls += 1
            return Generation("{}", "test")

    generator = Generator()
    with pytest.raises(SummaryError, match="after one correction"):
        summarize(transcript(), "test", generator)
    assert generator.calls == 2


@pytest.mark.parametrize("pronoun", ["me", "us", "them", "myself"])
def test_object_pronouns_cannot_be_names(pronoun):
    from meeting_intelligence.action_extraction import resolve_owner
    from meeting_intelligence.action_schemas import GeneratedOwner
    from meeting_intelligence.summarization import SummaryError

    owner = GeneratedOwner(kind="person", mention=pronoun, evidence=[{"segment_id": "seg_00000"}])
    with pytest.raises(SummaryError, match="not an explicitly named person"):
        resolve_owner(owner, transcript("Assign this to " + pronoun))
