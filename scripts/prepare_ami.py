"""Convert AMI manual XML into timestamped references without LLM inference."""

import argparse
import csv
import json
import re
import wave
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NITE = "{http://nite.sourceforge.net/}"


def read_meeting(archive, meeting):
    words_by_file = {}
    words = []
    for name in sorted(archive.namelist()):
        if not name.startswith(f"words/{meeting}.") or not name.endswith(".words.xml"):
            continue
        speaker = Path(name).name.split(".")[1]
        entries = list(ET.fromstring(archive.read(name)))
        words_by_file[Path(name).name] = entries
        for node in entries:
            if node.tag != "w" or node.get("punc") == "true" or not node.text:
                continue
            start, end = float(node.attrib["starttime"]), float(node.attrib["endtime"])
            if end < start:
                raise ValueError(f"Invalid word timestamps: {node.attrib}")
            words.append(
                {
                    "id": node.attrib[NITE + "id"],
                    "speaker_id": speaker,
                    "start": start,
                    "end": end,
                    "text": node.text.strip(),
                }
            )
    by_id = {word["id"]: word for word in words}
    segments = []
    covered = []
    for name in sorted(archive.namelist()):
        if not name.startswith(f"segments/{meeting}.") or not name.endswith(".segments.xml"):
            continue
        speaker = Path(name).name.split(".")[1]
        for node in ET.fromstring(archive.read(name)):
            selected = []
            for child in node.findall(NITE + "child"):
                filename, fragment = child.attrib["href"].split("#", 1)
                ids = re.findall(r"id\(([^)]+)\)", fragment)
                entries = words_by_file[filename]
                positions = {item.attrib[NITE + "id"]: i for i, item in enumerate(entries)}
                left, right = positions[ids[0]], positions[ids[-1]]
                if right < left:
                    raise ValueError("Reversed AMI word range")
                selected.extend(
                    by_id[item.attrib[NITE + "id"]]
                    for item in entries[left : right + 1]
                    if item.attrib[NITE + "id"] in by_id
                )
            if not selected:
                continue
            covered.extend(word["id"] for word in selected)
            segments.append(
                {
                    "id": node.attrib[NITE + "id"],
                    "speaker_id": speaker,
                    "start": min(word["start"] for word in selected),
                    "end": max(word["end"] for word in selected),
                    "text": " ".join(word["text"] for word in selected),
                    "word_ids": [word["id"] for word in selected],
                }
            )
    if set(covered) != set(by_id) or len(covered) != len(set(covered)):
        raise ValueError(f"{meeting}: segment coverage missing or duplicated words")
    words.sort(key=lambda word: (word["start"], word["speaker_id"], word["end"]))
    segments.sort(key=lambda segment: (segment["start"], segment["speaker_id"]))
    summary = {}
    name = f"abstractive/{meeting}.abssumm.xml"
    if name in archive.namelist():
        for section in ET.fromstring(archive.read(name)):
            summary[section.tag] = [
                {
                    "source_id": sentence.get(NITE + "id"),
                    "text": "".join(sentence.itertext()).strip(),
                }
                for sentence in section.findall("sentence")
            ]
    return {
        "meeting_id": meeting,
        "source": "AMI manual annotations v1.6.2",
        "reference_type": "corpus human annotation; mechanically converted",
        "speaker_ids": sorted({word["speaker_id"] for word in words}),
        "segments": segments,
        "words": words,
        "original_summary_sections": summary,
        "annotation_gaps": [
            "structured owners and deadlines require review",
            "decision change histories require review",
            "QA reference answers require annotation",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root
    provenance = json.loads((root / "provenance.json").read_text())
    references = root / "references"
    references.mkdir(exist_ok=True)
    rows = []
    with zipfile.ZipFile(root / "source" / "ami_public_manual_1.6.2.zip") as archive:
        for item in provenance["meetings"]:
            meeting = item["meeting_id"]
            reference = read_meeting(archive, meeting)
            assert reference["words"] and reference["segments"]
            assert max(word["end"] for word in reference["words"]) <= item["duration_seconds"] + 1
            target = references / f"{meeting}.json"
            target.write_text(json.dumps(reference, indent=2, ensure_ascii=False), encoding="utf-8")
            (references / f"{meeting}.txt").write_text(
                "\n".join(
                    f"[{segment['start']:.2f}-{segment['end']:.2f}] {segment['speaker_id']}: {segment['text']}"
                    for segment in reference["segments"]
                ),
                encoding="utf-8",
            )
            rows.append(
                {
                    "meeting_id": meeting,
                    "recording_path": item["path"],
                    "reference_path": str(target.resolve()),
                    "language": "en",
                    "meeting_date": "",
                    "timezone": "",
                    "split": item["split"],
                    "source": item["source_url"],
                    "notes": "AMI human references; project subset",
                }
            )
            print(
                f"{meeting}: {len(reference['words'])} words, {len(reference['segments'])} segments, "
                f"{len(reference['speaker_ids'])} speakers; all words covered once.",
                flush=True,
            )
    with (root / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    # Freeze development-only windows before running either model.
    meeting = "ES2002a"
    reference = json.loads((references / f"{meeting}.json").read_text(encoding="utf-8"))
    clips = root / "benchmark_clips"
    clips.mkdir(exist_ok=True)
    windows = []
    for start, end in [(60, 120), (600, 660), (900, 960)]:
        if start < min(word["start"] for word in reference["words"]) or end > max(
            word["end"] for word in reference["words"]
        ):
            raise ValueError("Benchmark window extends outside manual annotation coverage")
        clip_id = f"{meeting}_{start:04d}_{end:04d}"
        path = clips / f"{clip_id}.wav"
        with wave.open(str(root / "recordings" / f"{meeting}.Mix-Headset.wav")) as source:
            rate = source.getframerate()
            params = source.getparams()
            source.setpos(start * rate)
            frames = source.readframes((end - start) * rate)
        with wave.open(str(path), "wb") as dest:
            dest.setparams(params)
            dest.writeframes(frames)
        selected = [
            word for word in reference["words"] if start <= (word["start"] + word["end"]) / 2 < end
        ]
        text = " ".join(word["text"] for word in selected)
        assert text
        windows.append(
            {
                "clip_id": clip_id,
                "meeting_id": meeting,
                "split": "development",
                "audio_path": str(path.resolve()),
                "start": start,
                "end": end,
                "reference_text": text,
                "reference_word_ids": [word["id"] for word in selected],
            }
        )
    (root / "benchmark_windows.json").write_text(
        json.dumps(
            {
                "version": 2,
                "purpose": "Day 1 CPU model comparison, not final held-out evaluation",
                "reference_policy": "Lexical words ordered by onset; midpoint inclusion at boundaries; punctuation and non-speech XML nodes excluded. Overlap is serialized by onset.",
                "windows": windows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print("Prepared three fixed 60-second development clips; held-out meeting not benchmarked.")


if __name__ == "__main__":
    main()
