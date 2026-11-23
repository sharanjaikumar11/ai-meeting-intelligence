"""Assign words by temporal overlap; never invent speaker identities."""

from collections import defaultdict

from .schemas import Segment, Turn, Word


def speaker_at(start: float, end: float, turns: list[Turn]) -> str | None:
    scores: dict[str, float] = defaultdict(float)
    for turn in turns:
        if start == end:
            if turn.start <= start < turn.end:
                scores[turn.speaker_id] += 1
        else:
            scores[turn.speaker_id] += max(0, min(end, turn.end) - max(start, turn.start))
    ranked = sorted(
        ((score, speaker) for speaker, score in scores.items() if score > 0), reverse=True
    )
    if not ranked or (len(ranked) > 1 and abs(ranked[0][0] - ranked[1][0]) < 1e-8):
        return None
    return ranked[0][1]


def overlaps(start: float, end: float, turns: list[Turn]) -> bool:
    relevant = [turn for turn in turns if turn.start < end and turn.end > start]
    for index, left in enumerate(relevant):
        for right in relevant[index + 1 :]:
            if left.speaker_id != right.speaker_id and max(start, left.start, right.start) < min(
                end, left.end, right.end
            ):
                return True
    return False


def align_segments(
    raw_segments: list[dict],
    exclusive: list[Turn],
    regular: list[Turn],
    duration: float,
    offset: float = 0,
    names: dict[str, str] | None = None,
) -> list[Segment]:
    names = names or {}
    aligned = []
    for index, raw in enumerate(raw_segments):
        source_id = f"asr_{index:05d}"
        words = []
        for item in raw.get("words", []):
            start, end = float(item["start"]), float(item["end"])
            if end < start or start < -0.1 or end > duration + 0.1:
                raise ValueError("ASR word timestamps outside audio bounds")
            start, end = max(0, start), min(duration, end)
            text = item["word"].strip()
            if not text:
                continue
            words.append(
                Word(
                    start=start + offset,
                    end=end + offset,
                    text=text,
                    probability=item.get("probability"),
                    speaker_id=speaker_at(start, end, exclusive),
                    overlapping_speech=overlaps(start, end, regular),
                )
            )
        if not words:
            text = raw.get("text", "").strip()
            if not text:
                continue
            start, end = float(raw["start"]), float(raw["end"])
            if end < start or start < -0.1 or end > duration + 0.1:
                raise ValueError("ASR segment timestamps outside audio bounds")
            start, end = max(0, start), min(duration, end)
            # Without word timing, do not attribute a multi-speaker sentence to one speaker.
            candidates = {
                turn.speaker_id for turn in exclusive if turn.start < end and turn.end > start
            }
            speaker = next(iter(candidates)) if len(candidates) == 1 else None
            aligned.append(
                Segment(
                    id=f"seg_{len(aligned):05d}",
                    source_segment_id=source_id,
                    start=start + offset,
                    end=end + offset,
                    text=text,
                    speaker_id=speaker,
                    speaker_name=names.get(speaker),
                    overlapping_speech=overlaps(start, end, regular),
                )
            )
            continue
        groups: list[list[Word]] = []
        for word in words:
            if not groups or groups[-1][-1].speaker_id != word.speaker_id:
                groups.append([])
            groups[-1].append(word)
        for group in groups:
            speaker = group[0].speaker_id
            aligned.append(
                Segment(
                    id=f"seg_{len(aligned):05d}",
                    source_segment_id=source_id,
                    start=min(word.start for word in group),
                    end=max(word.end for word in group),
                    text=" ".join(word.text for word in group),
                    speaker_id=speaker,
                    speaker_name=names.get(speaker),
                    words=group,
                    overlapping_speech=any(word.overlapping_speech for word in group),
                )
            )
    return sorted(aligned, key=lambda segment: (segment.start, segment.end))
