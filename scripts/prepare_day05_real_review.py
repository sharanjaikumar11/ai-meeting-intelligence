"""Prepare a supplementary DEVELOPMENT meeting; leave frozen test split untouched."""

import argparse
import hashlib
import json
import wave
import zipfile
from pathlib import Path

from download_ami import BASE, download
from prepare_ami import read_meeting


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-root", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--meeting", choices=["ES2002d", "EN2002d"], default="ES2002d")
    args = parser.parse_args()
    root = args.environment_root
    with zipfile.ZipFile(root / "data/source/ami_public_manual_1.6.2.zip") as archive:
        reference = read_meeting(archive, args.meeting)
    folder = root / "outputs/day05/real_review_source"
    if args.meeting != "ES2002d":
        folder = folder / args.meeting
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "reference.json").write_text(json.dumps(reference, indent=2), encoding="utf-8")
    for segment in reference["segments"]:
        if any(
            term in segment["text"].lower()
            for term in ["kinetic", "battery", "batteries", "deadline", "minutes", "instead"]
        ):
            print(f"{segment['start']:.2f}-{segment['end']:.2f}: {segment['text']}", flush=True)
    if args.download:
        url = (
            f"{BASE}/AMICorpusMirror/amicorpus/{args.meeting}/audio/{args.meeting}.Mix-Headset.wav"
        )
        if args.meeting == "EN2002d":
            url = f"{BASE}/AMICorpusMirror/amicorpus/HeadsetAudio/{args.meeting}.Mix-Headset.wav"
        recording = root / "data/recordings" / f"{args.meeting}.Mix-Headset.wav"
        download(url, recording)
        with wave.open(str(recording)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        (folder / "provenance.json").write_text(
            json.dumps(
                {
                    "meeting": args.meeting,
                    "split": "supplementary development, not held-out evaluation",
                    "selection": "Selected from human corpus annotations for design reversals (ES2002d) or the Friday-to-Monday deadline revision (EN2002d).",
                    "source_url": url,
                    "license": "CC BY 4.0",
                    "provider": "AMI Consortium",
                    "sha256": hashlib.sha256(recording.read_bytes()).hexdigest(),
                    "duration_seconds": duration,
                    "annotation_source": "AMI manual annotations v1.6.2; original archive retained under data/source",
                },
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
