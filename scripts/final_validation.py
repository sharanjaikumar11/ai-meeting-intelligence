"""Frozen final checks with one persistent 20-attempt Gemini budget."""

import argparse
import hashlib
import json
import sys
import time
import wave
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from complete_day08_budgeted import Budget
from download_ami import BASE, download
from prepare_ami import read_meeting
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.alignment import align_segments
from meeting_intelligence.pipeline import transcribe
from meeting_intelligence.qa import INSTRUCTION, GeneratedAnswer, QAReviewGenerator, ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import settings_from_environment


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def paths(root):
    return root / "outputs/day10/final_2026-11-23"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument(
        "--stage", choices=["prepare", "transcribe", "followups", "extract"], required=True
    )
    a = p.parse_args()
    root = a.environment_root
    out = paths(root)
    out.mkdir(parents=True, exist_ok=True)
    gold_path = REPO / "evaluation/day10_unseen_gold.json"
    gold = json.loads(gold_path.read_text())
    files = [
        gold_path,
        Path(__file__),
        REPO / "scripts/complete_day08_budgeted.py",
        *sorted((REPO / "meeting_intelligence").glob("*.py")),
    ]
    hashes = {str(f.relative_to(REPO)): sha(f) for f in files}
    freeze = out / "freeze.json"
    if freeze.exists():
        if json.loads(freeze.read_text())["source_sha256"] != hashes:
            raise RuntimeError("Frozen candidate changed")
    elif a.stage == "prepare":
        write(
            freeze,
            dict(
                created_utc=datetime.now(timezone.utc).isoformat(),
                source_sha256=hashes,
                task_count=sum(len(c["actions"]) for c in gold["cases"]),
                settings=dict(
                    model="small",
                    beam_size=5,
                    diarization_context=0,
                    threads=4,
                    gemini="gemini-2.5-flash",
                    request_limit=20,
                ),
                annotation="Assistant annotation from corpus human references; no independent human label review.",
                selection="Six task-rich project-unseen excerpts; not official test split or broad meeting distribution.",
            ),
        )
    else:
        raise RuntimeError("Prepare and freeze first")
    if a.stage == "prepare":
        archive = root / "data/source/ami_public_manual_1.6.2.zip"
        with zipfile.ZipFile(archive) as z:
            for c in gold["cases"]:
                ref = read_meeting(z, c["meeting"])
                words = [
                    w for w in ref["words"] if c["start"] <= (w["start"] + w["end"]) / 2 < c["end"]
                ]
                segments = [
                    s for s in ref["segments"] if s["end"] > c["start"] and s["start"] < c["end"]
                ]
                ids = {s["id"] for s in segments}
                for task in c["actions"]:
                    if not set(task["evidence"]) <= ids:
                        raise ValueError("Reference outside interval")
                write(
                    out / f"{c['id']}.reference.json",
                    dict(words=words, segments=segments, text=" ".join(w["text"] for w in words)),
                )

        def get(c):
            path = root / "data/recordings" / f"{c['meeting']}.Mix-Headset.wav"
            url = f"{BASE}/AMICorpusMirror/amicorpus/{c['meeting']}/audio/{path.name}"
            download(url, path)
            with wave.open(str(path)) as w:
                duration = w.getnframes() / w.getframerate()
            if duration < c["end"]:
                raise ValueError("Recording too short")
            return dict(
                case=c["id"],
                url=url,
                path=str(path),
                sha256=sha(path),
                reference_sha256=sha(out / f"{c['id']}.reference.json"),
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            records = list(pool.map(get, gold["cases"]))
        write(out / "provenance.json", dict(annotation_sha256=sha(archive), recordings=records))
        print("Six recordings and 20 reference tasks prepared before predictions.", flush=True)
        return
    if a.stage == "transcribe":
        import jiwer
        from whisper.normalizers import EnglishTextNormalizer

        normalize = EnglishTextNormalizer()
        records = json.loads((out / "provenance.json").read_text())["recordings"]
        for c in gold["cases"]:
            record = next(r for r in records if r["case"] == c["id"])
            if sha(Path(record["path"])) != record["sha256"]:
                raise ValueError("Audio changed")
            dest = out / f"{c['id']}.transcript.json"
            if not dest.exists():
                print("Transcribing", c["id"], flush=True)
                start = time.perf_counter()
                t = transcribe(
                    Path(record["path"]),
                    root,
                    start=c["start"],
                    duration=c["end"] - c["start"],
                    beam_size=5,
                    diarization_context=0,
                )
                dest.write_text(t.model_dump_json(indent=2), encoding="utf-8")
                write(out / f"{c['id']}.timing.json", dict(seconds=time.perf_counter() - start))
            t = Transcript.model_validate_json(dest.read_text())
            ref = json.loads((out / f"{c['id']}.reference.json").read_text())
            r, h = normalize(ref["text"]), normalize(t.text)
            m = jiwer.process_words(r, h)
            write(
                out / f"{c['id']}.wer.json",
                dict(
                    reference=r,
                    hypothesis=h,
                    wer=m.wer,
                    substitutions=m.substitutions,
                    deletions=m.deletions,
                    insertions=m.insertions,
                    reference_words=m.hits + m.substitutions + m.deletions,
                    transcript_sha256=sha(dest),
                ),
            )
            print(c["id"], "WER", round(m.wer, 4), flush=True)
        return
    settings = settings_from_environment(root)
    if settings.model != "gemini-2.5-flash":
        raise ValueError("Unexpected model")
    budget = Budget(out, 20)

    def action(t, path):
        if path.exists():
            return
        result = extract_actions(
            t, settings.model, budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION)
        )
        verify(dict(transcript=t.model_dump(mode="json"), actions=result.model_dump(mode="json")))
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    def question(t, q, path):
        if path.exists():
            return
        result = ask(
            t,
            q,
            settings.model,
            QAReviewGenerator(budget.generator(settings, GeneratedAnswer, INSTRUCTION)),
        )
        verify(dict(transcript=t.model_dump(mode="json"), qa=result.model_dump(mode="json")))
        path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    if a.stage == "followups":
        raw = json.loads((root / "outputs/day10/recall_audio_probe/beam5.json").read_text())
        t = Transcript(
            source_file=str(root / "data/recordings/IS1003b.Mix-Headset.wav"),
            source_duration_seconds=1646,
            processed_start_seconds=1555,
            processed_duration_seconds=30,
            language="en",
            asr_model="small",
            diarization_model=None,
            diarization_status="skipped",
            text=raw["text"],
            speakers=[],
            segments=align_segments(raw["segments"], [], [], 30, 1555, {}),
            diarization_turns=[],
            exclusive_diarization_turns=[],
            warnings=[
                "Focused beam-5 audio review. No speaker identities inferred; roles must be explicit in speech."
            ],
        )
        (out / "recovered.transcript.json").write_text(
            t.model_dump_json(indent=2), encoding="utf-8"
        )
        action(t, out / "recovered.actions.json")
        question(
            t,
            "What should the Industrial Designer and User Interface Designer work on next?",
            out / "recovered.qa.json",
        )
        original = Transcript.model_validate_json(
            (root / "outputs/day09/ES2004d_1420_1660.transcript.json").read_text()
        )
        action(original, out / "recommendation.actions.json")
        question(
            original,
            "What was finally decided about voice recognition, and why?",
            out / "budget.qa.json",
        )
    else:
        for c in gold["cases"]:
            print("Extracting", c["id"], flush=True)
            t = Transcript.model_validate_json((out / f"{c['id']}.transcript.json").read_text())
            action(t, out / f"{c['id']}.actions.json")
    print("Finished; attempts:", len(budget.entries), flush=True)


if __name__ == "__main__":
    main()
