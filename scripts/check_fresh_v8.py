"""Frozen fresh-meeting evaluation, with a new ledger only after the Pacific reset."""

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import Budget
from download_ami import download
from download_final_mirror import get_json
from prepare_ami import read_meeting
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.pipeline import transcribe
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import settings_from_environment


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--stage", choices=["prepare", "transcribe", "extract"], required=True)
    a = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = a.environment_root
    out = root / "outputs/day10/fresh_v8_ES2009a"
    out.mkdir(parents=True, exist_ok=True)
    gold_path = repo / "evaluation/fresh_v8_gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    files = [
        gold_path,
        Path(__file__),
        repo / "scripts/complete_day08_budgeted.py",
        repo / "scripts/prepare_ami.py",
        *sorted((repo / "meeting_intelligence").glob("*.py")),
    ]
    hashes = {str(f.relative_to(repo)): sha(f) for f in files}
    freeze = out / "freeze.json"
    if freeze.exists():
        if json.loads(freeze.read_text(encoding="utf-8"))["source_sha256"] != hashes:
            raise ValueError("Frozen candidate or labels changed")
    elif a.stage == "prepare":
        write(
            freeze,
            dict(
                source_sha256=hashes,
                created_utc=datetime.now(timezone.utc).isoformat(),
                settings=dict(
                    whisper="small", beam_size=5, diarization_context=0, gemini="gemini-2.5-flash"
                ),
            ),
        )
    else:
        raise ValueError("Prepare and freeze first")
    if a.stage == "prepare":
        archive = root / "data/source/ami_public_manual_1.6.2.zip"
        with zipfile.ZipFile(archive) as z:
            full = read_meeting(z, "ES2009a")
        for c in gold["cases"]:
            words = [
                w for w in full["words"] if c["start"] <= (w["start"] + w["end"]) / 2 < c["end"]
            ]
            segments = [
                s for s in full["segments"] if s["end"] > c["start"] and s["start"] < c["end"]
            ]
            for task in c["actions"]:
                assert set(task["evidence"]) <= {s["id"] for s in segments}
            write(
                out / f"{c['id']}.reference.json",
                dict(words=words, segments=segments, text=" ".join(w["text"] for w in words)),
            )
        mirror = "ggfox00000/dia-AMICorpus-all"
        revision = "a249db53de253a3a0a864c93a51d613159dfec7c"
        entries = get_json(
            f"https://huggingface.co/api/datasets/{mirror}/tree/{revision}/amicorpus/ES2009a/audio?limit=100"
        )
        entry = next(e for e in entries if e["path"].endswith("Mix-Headset.wav"))
        audio = root / "data/recordings/ES2009a.Mix-Headset.wav"
        url = f"https://huggingface.co/datasets/{mirror}/resolve/{revision}/{entry['path']}"
        download(url, audio)
        assert sha(audio) == entry["lfs"]["oid"] and audio.stat().st_size == entry["size"]
        write(
            out / "provenance.json",
            dict(
                annotation_sha256=sha(archive),
                mirror=mirror,
                revision=revision,
                recordings=[
                    dict(
                        case=c["id"],
                        path=str(audio),
                        url=url,
                        sha256=sha(audio),
                        reference_sha256=sha(out / f"{c['id']}.reference.json"),
                    )
                    for c in gold["cases"]
                ],
            ),
        )
        print("Frozen references and hash-verified fresh recording ready.", flush=True)
        return
    if a.stage == "transcribe":
        import jiwer
        from whisper.normalizers import EnglishTextNormalizer

        norm = EnglishTextNormalizer()
        provenance = json.loads((out / "provenance.json").read_text(encoding="utf-8"))
        for c in gold["cases"]:
            record = next(r for r in provenance["recordings"] if r["case"] == c["id"])
            assert sha(Path(record["path"])) == record["sha256"]
            dest = out / f"{c['id']}.transcript.json"
            if not dest.exists():
                print("Transcribing", c["id"], flush=True)
                t = transcribe(
                    Path(record["path"]),
                    root,
                    start=c["start"],
                    duration=c["end"] - c["start"],
                    beam_size=5,
                    diarization_context=0,
                )
                dest.write_text(t.model_dump_json(indent=2), encoding="utf-8")
            t = Transcript.model_validate_json(dest.read_text(encoding="utf-8"))
            ref = json.loads((out / f"{c['id']}.reference.json").read_text(encoding="utf-8"))
            r, h = norm(ref["text"]), norm(t.text)
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
            print(c["id"], "WER", m.wer, flush=True)
        return
    reset = datetime(2026, 11, 23, 8, tzinfo=timezone.utc)
    if datetime.now(timezone.utc) < reset:
        raise RuntimeError(
            "Previous daily budget exhausted; do not call Gemini before 08:00 UTC / 13:30 IST."
        )
    budget_dir = root / "outputs/gemini_budget/2026-11-23-pacific"
    budget_dir.mkdir(parents=True, exist_ok=True)
    budget = Budget(budget_dir, 20)
    settings = settings_from_environment(root)
    assert settings.model == "gemini-2.5-flash"
    for c in gold["cases"]:
        dest = out / f"{c['id']}.actions.json"
        if dest.exists():
            continue
        t = Transcript.model_validate_json(
            (out / f"{c['id']}.transcript.json").read_text(encoding="utf-8")
        )
        result = extract_actions(
            t, settings.model, budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION)
        )
        verify(dict(transcript=t.model_dump(mode="json"), actions=result.model_dump(mode="json")))
        dest.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print("Extracted", c["id"], len(result.action_items), "tasks", flush=True)


if __name__ == "__main__":
    main()
