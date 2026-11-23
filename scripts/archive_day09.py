"""Archive public evaluation evidence and frozen source, excluding credentials/audio."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument(
        "--partial",
        action="store_true",
        help="Archive completed local work with an explicit incomplete-run name.",
    )
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    out = a.environment_root / "outputs/day09"
    required = "local_metrics.json" if a.partial else "metrics.json"
    if not (out / required).exists():
        raise RuntimeError("Score the selected run status before archiving")
    frozen = json.loads((out / "freeze.json").read_text())
    sources = {repo / rel for rel in frozen["source_sha256"]}
    for rel, expected in frozen["source_sha256"].items():
        if hashlib.sha256((repo / rel).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Frozen source changed")
    sources.update(
        repo / rel
        for rel in [
            "scripts/download_ami.py",
            "scripts/score_day09.py",
            "scripts/archive_day09.py",
            "tests/test_day09.py",
            "evaluation/README.md",
            "docs/DAY_09.md",
        ]
    )
    if not a.partial:
        sources.add(repo / "evaluation/day09_metrics.json")
    sources.add(
        repo
        / "evaluation"
        / ("day09_review_progress.json" if a.partial else "day09_adjudication.json")
    )
    target = out / ("day09_partial_evidence.zip" if a.partial else "day09_evaluation_bundle.zip")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(sources):
            z.write(f, "source/" + f.relative_to(repo).as_posix())
        # Explicit extensions and scope: no .env, models, recordings or unrelated outputs.
        for f in sorted(out.rglob("*.json")):
            z.write(f, "outputs/day09/" + f.relative_to(out).as_posix())
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None:
            raise RuntimeError("Archive validation failed")
    print(
        json.dumps(
            dict(
                path=str(target),
                bytes=target.stat().st_size,
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            )
        )
    )


if __name__ == "__main__":
    main()
