import pytest
from test_day03 import transcript

from meeting_intelligence.correct_speakers import apply_corrections
from meeting_intelligence.schemas import Speaker, Turn


def source():
    t = transcript()
    t.diarization_status = "completed"
    t.speakers = [Speaker(id="A"), Speaker(id="B")]
    t.exclusive_diarization_turns = [Turn(start=60, end=120, speaker_id="A")]
    return t


def test_review_splits_turns_preserves_source_and_marks_supervision():
    t = source()
    result = apply_corrections(
        t, [{"start": 65, "end": 70, "speaker_id": "B", "reason": "Reviewed source"}]
    )
    assert [(v.start, v.end, v.speaker_id) for v in result.exclusive_diarization_turns] == [
        (60, 65, "A"),
        (65, 70, "B"),
        (70, 120, "A"),
    ]
    assert result.segments[0].speaker_id == "B"
    assert len(t.exclusive_diarization_turns) == 1
    assert "human-reference-assisted" in result.warnings[-1]


@pytest.mark.parametrize(
    "patch",
    [
        {"start": 59, "end": 70, "speaker_id": "B", "reason": "review"},
        {"start": 65, "end": 70, "speaker_id": "C", "reason": "review"},
        {"start": 65, "end": 70, "speaker_id": "B", "reason": ""},
    ],
)
def test_invalid_review_rejected(patch):
    with pytest.raises(ValueError):
        apply_corrections(source(), [patch])
