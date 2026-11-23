import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from meeting_intelligence.__main__ import timestamp
from meeting_intelligence.alignment import align_segments, overlaps, speaker_at
from meeting_intelligence.diarization import DiarizationAccessError, require_access_token
from meeting_intelligence.media import decode, ffmpeg_tools, probe_media
from meeting_intelligence.schemas import Transcript, Turn


def turn(start, end, speaker):
    return Turn(start=start, end=end, speaker_id=speaker)


def raw(words):
    return [{"start": 0, "end": 3, "text": "Hello there again", "words": words}]


def test_splits_at_speaker_changes_and_preserves_original_offset():
    words = [
        {"start": 0, "end": 1, "word": " Hello"},
        {"start": 1, "end": 2, "word": " there"},
        {"start": 2, "end": 3, "word": " again"},
    ]
    turns = [turn(0, 1, "A"), turn(1, 3, "B")]
    segments = align_segments(raw(words), turns, turns, 3, 60, {"A": "Alice"})
    assert [segment.text for segment in segments] == ["Hello", "there again"]
    assert [segment.speaker_id for segment in segments] == ["A", "B"]
    assert [(segment.start, segment.end) for segment in segments] == [(60, 61), (61, 63)]
    assert segments[0].speaker_name == "Alice"
    assert segments[1].speaker_name is None


def test_gap_does_not_inherit_nearest_speaker():
    assert speaker_at(2, 3, [turn(0, 1, "A"), turn(4, 5, "B")]) is None


def test_equal_temporal_overlap_remains_unknown():
    assert speaker_at(0, 2, [turn(0, 1, "A"), turn(1, 2, "B")]) is None


def test_zero_duration_word_uses_half_open_boundary():
    assert speaker_at(1, 1, [turn(0, 1, "A"), turn(1, 2, "B")]) == "B"


def test_overlap_flag_requires_simultaneous_speakers():
    assert not overlaps(0, 2, [turn(0, 1, "A"), turn(1, 2, "B")])
    assert overlaps(0, 2, [turn(0, 1.5, "A"), turn(1, 2, "B")])


def test_unsupported_word_kept_without_speaker():
    segments = align_segments(raw([{"start": 0, "end": 1, "word": " Hello"}]), [], [], 3)
    assert segments[0].text == "Hello"
    assert segments[0].speaker_id is None


def test_segment_without_words_is_not_assigned_across_speakers():
    segments = align_segments(
        [{"start": 0, "end": 3, "text": "Keep all text."}],
        [turn(0, 1, "A"), turn(1, 3, "B")],
        [],
        3,
    )
    assert segments[0].speaker_id is None
    assert segments[0].text == "Keep all text."


def test_bad_asr_timestamps_rejected():
    with pytest.raises(ValueError, match="bounds"):
        align_segments(raw([{"start": 2, "end": 1, "word": "bad"}]), [], [], 3)


def test_timestamp_rounding_carries_minutes():
    assert timestamp(59.9999) == "00:01:00.000"


def test_missing_token_error_is_actionable(monkeypatch, tmp_path):
    monkeypatch.setattr("meeting_intelligence.diarization.get_access_token", lambda root: None)
    with pytest.raises(DiarizationAccessError, match="HF_TOKEN"):
        require_access_token(tmp_path)


def test_schema_rejects_nonfinite_and_reversed_timestamps():
    with pytest.raises(ValidationError):
        turn(float("nan"), 1, "A")
    with pytest.raises(ValidationError):
        turn(2, 1, "A")


def test_schema_rejects_speakers_when_diarization_skipped():
    with pytest.raises(ValidationError, match="Skipped diarization"):
        Transcript(
            source_file="sample.wav",
            source_duration_seconds=2,
            processed_start_seconds=0,
            processed_duration_seconds=2,
            language="en",
            asr_model="small",
            diarization_model=None,
            diarization_status="skipped",
            text="",
            speakers=[{"id": "A"}],
            segments=[],
            diarization_turns=[],
            exclusive_diarization_turns=[],
        )


@pytest.fixture
def media_tools():
    import os

    root = os.environ.get("MEETING_ENV_ROOT")
    if not root:
        pytest.skip("Set MEETING_ENV_ROOT for real FFmpeg integration tests")
    return ffmpeg_tools(Path(root))


def test_video_audio_extraction_and_offset(tmp_path, media_tools):
    ffmpeg, ffprobe = media_tools
    video = tmp_path / "meeting with spaces.mp4"
    subprocess.run(
        [
            str(ffmpeg),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=1:d=3",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=3",
            "-c:v",
            "mpeg4",
            "-c:a",
            "aac",
            "-shortest",
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    media = probe_media(video, ffprobe)
    actual = decode(video, tmp_path / "decoded.wav", ffmpeg, media["audio_stream_index"], 1, 1)
    assert actual == pytest.approx(1, abs=0.01)


def test_video_without_audio_rejected(tmp_path, media_tools):
    ffmpeg, ffprobe = media_tools
    video = tmp_path / "silent_video.mp4"
    subprocess.run(
        [
            str(ffmpeg),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x64:r=1:d=1",
            "-an",
            "-c:v",
            "mpeg4",
            str(video),
        ],
        check=True,
        capture_output=True,
    )
    with pytest.raises(ValueError, match="no audio"):
        probe_media(video, ffprobe)


def test_corrupt_recording_rejected(tmp_path, media_tools):
    _, ffprobe = media_tools
    source = tmp_path / "bad.wav"
    source.write_text("not audio")
    with pytest.raises(ValueError, match="cannot be decoded"):
        probe_media(source, ffprobe)


@pytest.mark.parametrize("beam_size", [None, 5])
def test_pipeline_integration_with_mocked_model_outputs(
    tmp_path, media_tools, monkeypatch, beam_size
):
    """Checks adapter wiring; deliberately not a diarization model inference test."""
    import os

    import whisper

    from meeting_intelligence import pipeline

    ffmpeg, _ = media_tools
    source = tmp_path / "audio.wav"
    subprocess.run(
        [
            str(ffmpeg),
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=3",
            str(source),
        ],
        check=True,
        capture_output=True,
    )

    class Model:
        def transcribe(self, path, **kwargs):
            assert kwargs["word_timestamps"] is True
            assert kwargs.get("beam_size") == beam_size
            if beam_size is None:
                assert "beam_size" not in kwargs
            return {
                "language": "en",
                "text": "Hello there",
                "segments": raw(
                    [
                        {"start": 0, "end": 0.5, "word": "Hello"},
                        {"start": 0.5, "end": 1, "word": "there"},
                    ]
                ),
            }

    monkeypatch.setattr(whisper, "load_model", lambda *args, **kwargs: Model())
    monkeypatch.setattr(
        pipeline.diarization, "require_access_token", lambda root: "mock-not-a-token"
    )
    turns = [turn(0, 0.5, "A"), turn(0.5, 1, "B")]
    monkeypatch.setattr(pipeline.diarization, "run", lambda *args: (turns, turns))
    result = pipeline.transcribe(
        source,
        Path(os.environ["MEETING_ENV_ROOT"]),
        start=1,
        duration=1,
        speaker_names={"A": "Alice"},
        beam_size=beam_size,
    )
    assert result.diarization_status == "completed"
    assert [segment.start for segment in result.segments] == [1, 1.5]
    assert result.segments[0].speaker_name == "Alice"
    assert result.exclusive_diarization_turns[0].start == 1
    assert "mock-not-a-token" not in result.model_dump_json()


def test_cli_refuses_existing_output(tmp_path, monkeypatch):
    from meeting_intelligence.__main__ import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "meeting",
            "irrelevant.wav",
            "--environment-root",
            str(tmp_path),
            "--output",
            str(tmp_path),
        ],
    )
    assert main() == 1
