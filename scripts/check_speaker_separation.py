"""Development diagnostic: reference-word midpoint speaker attribution, not DER."""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from meeting_intelligence.schemas import Transcript


def score(reference, transcript):
    lo = transcript.processed_start_seconds
    hi = lo + transcript.processed_duration_seconds
    words = [w for w in reference["words"] if lo <= (w["start"] + w["end"]) / 2 < hi]
    samples = []
    excluded = 0
    for word in words:
        midpoint = (word["start"] + word["end"]) / 2
        speakers = {w["speaker_id"] for w in words if w["start"] <= midpoint < w["end"]}
        if len(speakers) != 1:
            excluded += 1
            continue
        predicted = {
            t.speaker_id
            for t in transcript.exclusive_diarization_turns
            if t.start <= midpoint < t.end
        }
        samples.append((word["speaker_id"], next(iter(predicted)) if len(predicted) == 1 else None))
    truth = sorted({a for a, _ in samples})
    predicted = sorted({b for _, b in samples if b is not None})
    counts = Counter(samples)
    matrix = np.array([[counts[(a, b)] for b in predicted] for a in truth])
    rows, columns = linear_sum_assignment(-matrix)
    correct = int(sum(matrix[r, c] for r, c in zip(rows, columns)))
    mapping = {predicted[c]: truth[r] for r, c in zip(rows, columns)}
    return {
        "reference_speaker_count": len(truth),
        "predicted_speaker_count": len(transcript.speakers),
        "scored_nonoverlap_word_midpoints": len(samples),
        "excluded_overlap_or_zero_length_words": excluded,
        "correct_after_optimal_label_mapping": correct,
        "speaker_accuracy_on_scored_midpoints": correct / len(samples) if samples else None,
        "unassigned_midpoints": sum(b is None for _, b in samples),
        "label_mapping_for_evaluation_only": mapping,
        "reference_labels": truth,
        "predicted_labels": predicted,
        "confusion_counts": matrix.tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("transcripts", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    report = {
        "method": "Single-reference-speaker word midpoint scoring with optimal global label permutation. Includes missing predictions as errors. Not DER, not name identification, not held-out accuracy.",
        "runs": {
            str(path): score(
                reference, Transcript.model_validate_json(path.read_text(encoding="utf-8"))
            )
            for path in args.transcripts
        },
    }
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
