"""Verified public mirror fallback; retain canonical and actual download provenance."""

import argparse
import hashlib
import json
import sys
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_ami import BASE, download


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    root = a.environment_root
    out = root / "outputs/day10/final_2026-11-23"
    repo = "ggfox00000/dia-AMICorpus-all"
    revision = get_json(f"https://huggingface.co/api/datasets/{repo}")["sha"]

    def metadata(meeting):
        files = get_json(
            f"https://huggingface.co/api/datasets/{repo}/tree/{revision}/amicorpus/{meeting}/audio?limit=100"
        )
        return next(f for f in files if f["path"].endswith("Mix-Headset.wav"))

    control = metadata("ES2004a")
    official = root / "data/recordings/ES2004a.Mix-Headset.wav"
    if sha(official) != control["lfs"]["oid"]:
        raise ValueError("Mirror control differs from official audio")
    gold = json.loads(
        (Path(__file__).resolve().parents[1] / "evaluation/day10_unseen_gold.json").read_text()
    )

    def fetch(c):
        f = metadata(c["meeting"])
        path = root / "data/recordings" / Path(f["path"]).name
        url = f"https://huggingface.co/datasets/{repo}/resolve/{revision}/{f['path']}"
        download(url, path)
        digest = sha(path)
        if digest != f["lfs"]["oid"] or path.stat().st_size != f["size"]:
            raise ValueError("Mirror file hash/size mismatch")
        with wave.open(str(path)) as w:
            duration = w.getnframes() / w.getframerate()
        if duration < c["end"]:
            raise ValueError("Audio shorter than frozen window")
        return dict(
            case=c["id"],
            url=url,
            canonical_url=f"{BASE}/AMICorpusMirror/amicorpus/{c['meeting']}/audio/{path.name}",
            path=str(path),
            sha256=digest,
            duration=duration,
            reference_sha256=sha(out / f"{c['id']}.reference.json"),
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(fetch, gold["cases"]))
    value = dict(
        annotation_sha256=sha(root / "data/source/ami_public_manual_1.6.2.zip"),
        mirror=repo,
        revision=revision,
        control_recording="ES2004a",
        control_sha256=sha(official),
        note="Third-party mirror; control file matches official download; all downloaded files verified against pinned LFS SHA-256. Official endpoint returned 503.",
        recordings=records,
    )
    (out / "provenance.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    print("All six recordings verified; provenance saved.", flush=True)


if __name__ == "__main__":
    main()
