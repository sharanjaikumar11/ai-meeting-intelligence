import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from score_day09 import extraction_score, pool_wer, prf, qa_score, sha, validate_wer


def test_one_to_one_matching_counts_omissions_and_false_positives():
    value = extraction_score(
        [{"id": "p1"}, {"id": "p2"}],
        [{"id": "g1"}, {"id": "g2"}],
        [
            {"prediction_id": "p1", "gold_id": "g1", "reason": "Same task"},
            {"prediction_id": "p2", "gold_id": None, "reason": "Unsupported task"},
        ],
    )
    assert (value["tp"], value["fp"], value["fn"], value["f1"]) == (1, 1, 1, 0.5)
    assert value["missed_gold_ids"] == ["g2"]


def test_duplicate_gold_match_cannot_inflate_recall():
    with pytest.raises(ValueError, match="one-to-one"):
        extraction_score(
            [{"id": "p1"}, {"id": "p2"}],
            [{"id": "g1"}],
            [{"prediction_id": p, "gold_id": "g1", "reason": "same"} for p in ["p1", "p2"]],
        )


def test_unreviewed_prediction_cannot_disappear():
    with pytest.raises(ValueError, match="exactly one"):
        extraction_score([{"id": "p1"}], [], [])


def test_unknown_gold_cannot_be_matched():
    with pytest.raises(ValueError, match="one-to-one"):
        extraction_score(
            [{"id": "p"}], [], [{"prediction_id": "p", "gold_id": "missing", "reason": "x"}]
        )


def test_empty_denominators_are_not_perfect_scores():
    assert prf(0, 0, 0)["f1"] is None
    assert prf(0, 0, 2) == dict(tp=0, fp=0, fn=2, precision=None, recall=0, f1=0)


def test_pooled_wer_uses_word_counts_not_mean_percentages():
    value = pool_wer(
        [
            dict(substitutions=1, deletions=0, insertions=0, reference_words=2),
            dict(substitutions=1, deletions=0, insertions=0, reference_words=98),
        ]
    )
    assert value["wer"] == 0.02 and value["word_errors"] == 2


def test_partial_qa_does_not_count_as_fully_correct():
    value = qa_score(
        [{}, {}],
        [
            dict(question_index=0, grade="full", reason="all facts"),
            dict(question_index=1, grade="partial", reason="missed owner"),
        ],
    )
    assert value["correctness"] == 0.5 and value["partial"] == 1


def test_missing_or_duplicate_qa_reviews_rejected():
    with pytest.raises(ValueError, match="exactly one"):
        qa_score([{}, {}], [dict(question_index=0, grade="full", reason="x")] * 2)


@pytest.mark.parametrize("corruption", [None, "counts", "interval", "reference"])
def test_wer_recomputed_against_pinned_reference(tmp_path, corruption):
    from test_day03 import transcript

    t = transcript("hello world")
    ref = tmp_path / "unit.reference.json"
    ref.write_text(json.dumps({"text": "hello world"}), encoding="utf-8")
    (tmp_path / "provenance.json").write_text(
        json.dumps({"recordings": [{"case": "unit", "reference_sha256": sha(ref)}]})
    )
    c = dict(id="unit", start=60, end=120)
    saved = dict(
        reference="hello world",
        hypothesis="hello world",
        substitutions=0,
        deletions=0,
        insertions=0,
        reference_words=2,
    )
    if corruption == "counts":
        saved["deletions"] = 1
    if corruption == "interval":
        c["end"] = 121
    if corruption == "reference":
        ref.write_text(json.dumps({"text": "different words"}))
    if corruption:
        with pytest.raises(ValueError):
            validate_wer(tmp_path, c, t, saved)
    else:
        assert validate_wer(tmp_path, c, t, saved)["wer"] == 0
