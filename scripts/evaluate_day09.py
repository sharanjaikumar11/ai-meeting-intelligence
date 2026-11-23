"""Frozen, resumable Day 9 pilot. No prompts or labels tuned by this runner."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
import time
import wave
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from complete_day08_budgeted import Budget, questions
from download_ami import BASE, download
from prepare_ami import read_meeting
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.decision_tracking import (
    INSTRUCTION,
    DecisionReviewGenerator,
    GeneratedDecisions,
    track_decisions,
)
from meeting_intelligence.pipeline import transcribe
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import SummaryError, settings_from_environment


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--stage", choices=["prepare", "transcribe", "extract"], required=True)
    a = p.parse_args()
    root = a.environment_root
    out = root / "outputs/day09"
    out.mkdir(parents=True, exist_ok=True)
    gold_path = REPO / "evaluation/day09_gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    files = [
        gold_path,
        REPO / "docs/DAY_09_PROTOCOL.md",
        Path(__file__),
        REPO / "scripts/complete_day08_budgeted.py",
        REPO / "scripts/prepare_ami.py",
        REPO / "scripts/verify_day08_live.py",
        *sorted((REPO / "meeting_intelligence").glob("*.py")),
    ]
    hashes = {str(f.relative_to(REPO)): digest(f) for f in files}
    frozen_path = out / "freeze.json"
    if frozen_path.exists():
        frozen = json.loads(frozen_path.read_text())
        if frozen["source_sha256"] != hashes:
            raise RuntimeError("Frozen source/gold changed; do not overwrite held-out run.")
    else:
        if a.stage != "prepare":
            raise RuntimeError("Prepare and freeze before inference.")
        frozen = dict(
            created_utc=datetime.now(timezone.utc).isoformat(),
            source_sha256=hashes,
            settings=dict(
                whisper="small",
                language="en",
                threads=4,
                diarization_context=300,
                gemini="gemini-2.5-flash",
                request_cap=20,
            ),
            packages={
                n: importlib.metadata.version(n)
                for n in [
                    "openai-whisper",
                    "torch",
                    "pyannote.audio",
                    "google-genai",
                    "jiwer",
                    "pydantic",
                ]
            },
        )
        write(frozen_path, frozen)
        write(out / "gold.json", gold)
    archive = root / "data/source/ami_public_manual_1.6.2.zip"
    if a.stage == "prepare":
        provenance = {"annotation_sha256": digest(archive), "recordings": []}
        with zipfile.ZipFile(archive) as z:
            for c in gold["cases"]:
                ref = read_meeting(z, c["meeting"])
                selected = [
                    w for w in ref["words"] if c["start"] <= (w["start"] + w["end"]) / 2 < c["end"]
                ]
                segments = [
                    s for s in ref["segments"] if s["end"] > c["start"] and s["start"] < c["end"]
                ]
                ids = {s["id"] for s in segments}
                for item in c["actions"] + c["decisions"] + c["qa"]:
                    if not set(item["evidence"]) <= ids:
                        raise ValueError("Gold evidence outside interval")
                write(
                    out / f"{c['id']}.reference.json",
                    dict(
                        words=selected,
                        segments=segments,
                        text=" ".join(w["text"] for w in selected),
                    ),
                )
                path = root / "data/recordings" / f"{c['meeting']}.Mix-Headset.wav"
                url = f"{BASE}/AMICorpusMirror/amicorpus/{c['meeting']}/audio/{path.name}"
                download(url, path)
                with wave.open(str(path)) as w:
                    duration = w.getnframes() / w.getframerate()
                    if duration < c["end"]:
                        raise ValueError("Recording too short")
                provenance["recordings"].append(
                    dict(
                        case=c["id"],
                        url=url,
                        path=str(path),
                        sha256=digest(path),
                        duration=duration,
                        reference_sha256=digest(out / f"{c['id']}.reference.json"),
                    )
                )
                write(out / "provenance.json", provenance)
        print("Prepared and frozen three cases before inference.", flush=True)
        return
    provenance = json.loads((out / "provenance.json").read_text())
    if len(provenance["recordings"]) != len(gold["cases"]):
        raise RuntimeError("Preparation incomplete")
    for record in provenance["recordings"]:
        if digest(Path(record["path"])) != record["sha256"]:
            raise RuntimeError("Audio changed")
        if digest(out / f"{record['case']}.reference.json") != record["reference_sha256"]:
            raise RuntimeError("Reference changed")
    if a.stage == "transcribe":
        import jiwer
        from whisper.normalizers import EnglishTextNormalizer

        normalize = EnglishTextNormalizer()
        for c in gold["cases"]:
            path = out / f"{c['id']}.transcript.json"
            started = time.perf_counter()
            if not path.exists():
                print("Transcribing", c["id"], flush=True)
                t = transcribe(
                    root / "data/recordings" / f"{c['meeting']}.Mix-Headset.wav",
                    root,
                    model_name="small",
                    language="en",
                    start=c["start"],
                    duration=c["end"] - c["start"],
                    threads=4,
                    diarization_context=300,
                )
                path.write_text(t.model_dump_json(indent=2), encoding="utf-8")
                write(
                    out / f"{c['id']}.timing.json",
                    dict(transcription_seconds=time.perf_counter() - started),
                )
            t = Transcript.model_validate_json(path.read_text(encoding="utf-8"))
            ref = json.loads((out / f"{c['id']}.reference.json").read_text(encoding="utf-8"))
            r, h = normalize(ref["text"]), normalize(t.text)
            m = jiwer.process_words(r, h)
            write(
                out / f"{c['id']}.wer.json",
                dict(
                    reference=r,
                    hypothesis=h,
                    substitutions=m.substitutions,
                    deletions=m.deletions,
                    insertions=m.insertions,
                    reference_words=m.hits + m.substitutions + m.deletions,
                    wer=m.wer,
                    transcript_sha256=digest(path),
                ),
            )
            print(c["id"], "WER", round(m.wer, 4), flush=True)
        return
    settings = settings_from_environment(root)
    if settings.model != frozen["settings"]["gemini"]:
        raise RuntimeError("Configured model differs from frozen protocol")
    budget = Budget(out, 20)
    for c in gold["cases"]:
        t = Transcript.model_validate_json(
            (out / f"{c['id']}.transcript.json").read_text(encoding="utf-8")
        )
        for name, fn in [
            (
                "actions",
                lambda: extract_actions(
                    t,
                    settings.model,
                    budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION),
                ).model_dump(mode="json"),
            ),
            (
                "decisions",
                lambda: track_decisions(
                    t,
                    settings.model,
                    DecisionReviewGenerator(
                        budget.generator(settings, GeneratedDecisions, INSTRUCTION, 16384)
                    ),
                ).model_dump(mode="json"),
            ),
            ("qa", lambda: questions(t, [q["question"] for q in c["qa"]], settings, budget)),
        ]:
            path = out / f"{c['id']}.{name}.json"
            if path.exists():
                continue
            print(c["id"], name, flush=True)
            try:
                value = fn()
                checks = [
                    verify({"transcript": t.model_dump(mode="json"), name: item})
                    for item in (value["answers"] if name == "qa" else [value])
                ]
                write(path, value)
                write(out / f"{c['id']}.{name}.integrity.json", checks)
            except Exception as exc:
                # Preserve failure explicitly; never replace with invented predictions.
                write(
                    out / f"{c['id']}.{name}.failure.json",
                    dict(
                        type=type(exc).__name__,
                        message=str(exc)
                        if isinstance(exc, SummaryError)
                        else "Stage failed; inspect locally",
                        attempts=len(budget.entries),
                    ),
                )
                raise
    print("All predictions saved; semantic adjudication required.", flush=True)


if __name__ == "__main__":
    main()
