"""Six-attempt development check on known Day 9 transcripts; not a new test set."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from complete_day08_budgeted import Budget, questions
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.qa import INSTRUCTION, GeneratedAnswer, ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import settings_from_environment


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    root = a.environment_root
    out = root / "outputs/day10/improvement_2026-11-22"
    out.mkdir(parents=True, exist_ok=True)
    original = root / "outputs/day09"
    gold = json.loads((REPO / "evaluation/day09_gold.json").read_text())
    reviews = json.loads((REPO / "evaluation/day09_adjudication.json").read_text())
    source = {
        str(f.relative_to(REPO)): sha(f)
        for f in [Path(__file__), *sorted((REPO / "meeting_intelligence").glob("*.py"))]
    }
    meta = out / "run_config.json"
    if meta.exists():
        if json.loads(meta.read_text())["source_sha256"] != source:
            raise RuntimeError("Development run source changed")
    else:
        meta.write_text(
            json.dumps(
                dict(
                    created_utc=datetime.now(timezone.utc).isoformat(),
                    source_sha256=source,
                    purpose="Known-example development recheck; not held-out improvement evidence",
                    gold_sha256=sha(REPO / "evaluation/day09_gold.json"),
                    limit=6,
                    qa_protocol="IS1003b two-question draft/review batch; ES2004d first question one-pass diagnostic to fit remaining quota. Other QA reused only for descriptive comparison.",
                ),
                indent=2,
            )
        )
    budget = Budget(out, 6)
    settings = settings_from_environment(root)
    for c in gold["cases"]:
        path = original / f"{c['id']}.transcript.json"
        if sha(path) != reviews["cases"][c["id"]]["prediction_sha256"]["transcript"]:
            raise RuntimeError("Baseline transcript changed")
        t = Transcript.model_validate_json(path.read_text())
        dest = out / f"{c['id']}.actions.json"
        if not dest.exists():
            r = extract_actions(
                t, settings.model, budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION)
            )
            verify(dict(transcript=t.model_dump(mode="json"), actions=r.model_dump(mode="json")))
            dest.write_text(r.model_dump_json(indent=2), encoding="utf-8")
    c = gold["cases"][2]
    t = Transcript.model_validate_json((original / f"{c['id']}.transcript.json").read_text())
    dest = out / f"{c['id']}.qa.json"
    if not dest.exists():
        r = questions(t, [q["question"] for q in c["qa"]], settings, budget)
        for answer in r["answers"]:
            verify(dict(transcript=t.model_dump(mode="json"), qa=answer))
        dest.write_text(json.dumps(r, indent=2), encoding="utf-8")
    c = gold["cases"][1]
    t = Transcript.model_validate_json((original / f"{c['id']}.transcript.json").read_text())
    dest = out / f"{c['id']}.qa_one_pass.json"
    if not dest.exists():
        r = ask(
            t,
            c["qa"][0]["question"],
            settings.model,
            budget.generator(settings, GeneratedAnswer, INSTRUCTION),
        )
        verify(dict(transcript=t.model_dump(mode="json"), qa=r.model_dump(mode="json")))
        dest.write_text(r.model_dump_json(indent=2), encoding="utf-8")
    print("Development checks saved; semantic review required.", flush=True)


if __name__ == "__main__":
    main()
