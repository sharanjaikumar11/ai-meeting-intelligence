"""Download a small public AMI meeting subset sequentially from Edinburgh."""

import argparse
import hashlib
import json
import urllib.request
import wave
import zipfile
from pathlib import Path

BASE = "https://groups.inf.ed.ac.uk/ami"
MEETINGS = {"ES2002a": "development", "ES2003a": "validation", "ES2004a": "test"}


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        print(f"Already present: {target.name}", flush=True)
        return
    partial = target.with_suffix(target.suffix + ".partial")
    print(f"Downloading {url}", flush=True)
    request = urllib.request.Request(
        url, headers={"User-Agent": "MeetingIntelligence-DatasetPreparation/1.0"}
    )
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
        expected = response.headers.get("Content-Length")
        count = 0
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            count += len(chunk)
        if expected is not None and count != int(expected):
            raise IOError(f"Incomplete download: {count}/{expected} bytes")
    partial.replace(target)
    print(f"Saved {target.name}: {count:,} bytes", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.data_root
    annotation_url = f"{BASE}/AMICorpusAnnotations/ami_public_manual_1.6.2.zip"
    archive = root / "source" / "ami_public_manual_1.6.2.zip"
    download(annotation_url, archive)
    with zipfile.ZipFile(archive) as contents:
        bad = contents.testzip()
        if bad:
            raise ValueError(f"Corrupt annotation entry: {bad}")
        print(f"Validated annotation archive: {len(contents.namelist())} entries", flush=True)
    records = []
    for meeting, split in MEETINGS.items():
        url = f"{BASE}/AMICorpusMirror/amicorpus/{meeting}/audio/{meeting}.Mix-Headset.wav"
        target = root / "recordings" / f"{meeting}.Mix-Headset.wav"
        download(url, target)
        with wave.open(str(target)) as audio:
            info = {
                "sample_rate": audio.getframerate(),
                "channels": audio.getnchannels(),
                "duration_seconds": audio.getnframes() / audio.getframerate(),
            }
        with target.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        records.append(
            {
                "meeting_id": meeting,
                "split": split,
                "language": "en",
                "path": str(target.resolve()),
                "source_url": url,
                "sha256": digest,
                **info,
            }
        )
        print(f"Validated {meeting}: {info}", flush=True)
    manifest = {
        "corpus": "AMI Meeting Corpus",
        "provider": "AMI Consortium / University of Edinburgh",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "source": f"{BASE}/download/",
        "annotations_url": annotation_url,
        "annotations_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "split_note": "Small project subset; not a claim of the full official benchmark.",
        "meetings": records,
    }
    (root / "provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Dataset download complete.", flush=True)


if __name__ == "__main__":
    main()
