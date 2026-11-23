"""Download three additional AMI recordings and retain human references/provenance."""

import argparse
import hashlib
import json
import wave
import zipfile
from pathlib import Path

from download_ami import BASE, download
from prepare_ami import read_meeting


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    args = p.parse_args()
    data = args.environment_root / "data"
    output = data / "day08"
    output.mkdir(exist_ok=True)
    records = []
    with zipfile.ZipFile(data / "source/ami_public_manual_1.6.2.zip") as archive:
        for meeting in ["ES2005a", "IS1001b", "TS3005d"]:
            target = data / "recordings" / f"{meeting}.Mix-Headset.wav"
            url = f"{BASE}/AMICorpusMirror/amicorpus/{meeting}/audio/{target.name}"
            download(url, target)
            with wave.open(str(target)) as audio:
                duration = audio.getnframes() / audio.getframerate()
            with target.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            reference = read_meeting(archive, meeting)
            (output / f"{meeting}.reference.json").write_text(
                json.dumps(reference, indent=2), encoding="utf-8"
            )
            records.append(
                dict(
                    meeting=meeting,
                    source_url=url,
                    path=str(target),
                    duration_seconds=duration,
                    sha256=digest,
                )
            )
            print(f"Validated {meeting}: {duration:.2f} seconds", flush=True)
    (output / "provenance.json").write_text(
        json.dumps(
            dict(
                source="https://groups.inf.ed.ac.uk/ami/download/",
                attribution="AMI Consortium / University of Edinburgh",
                license="CC BY 4.0",
                purpose="Day 8 development/error analysis; not an untouched Day 9 test set",
                recordings=records,
            ),
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
