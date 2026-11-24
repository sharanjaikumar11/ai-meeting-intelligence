"""Development regression on known transcripts; never label this unseen accuracy."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import Budget
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import settings_from_environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-root", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    root = args.environment_root
    out = root / "outputs/day10/release_v9"
    out.mkdir(parents=True, exist_ok=True)
    hashes = {
        str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(__file__).resolve(), *sorted((repo / "meeting_intelligence").glob("*.py"))]
    }
    manifest = out / "source_sha256.json"
    if manifest.exists():
        assert json.loads(manifest.read_text(encoding="utf-8")) == hashes, "Candidate changed"
    else:
        manifest.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    budget = Budget(root / "outputs/gemini_budget/2026-11-23-pacific", 20)
    settings = settings_from_environment(root)
    assert settings.model == "gemini-2.5-flash"
    for gold_name, source_folder in [
        ("day10_unseen_gold", "final_2026-11-23"),
        ("fresh_v8_gold", "fresh_v8_ES2009a"),
    ]:
        gold = json.loads((repo / "evaluation" / f"{gold_name}.json").read_text(encoding="utf-8"))
        for case in gold["cases"]:
            dest = out / f"{case['id']}.actions.json"
            if dest.exists():
                continue
            source = root / "outputs/day10" / source_folder / f"{case['id']}.transcript.json"
            transcript = Transcript.model_validate_json(source.read_text(encoding="utf-8"))
            print("Evaluating known case", case["id"], flush=True)
            result = extract_actions(
                transcript,
                settings.model,
                budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION),
            )
            verify(
                dict(
                    transcript=transcript.model_dump(mode="json"),
                    actions=result.model_dump(mode="json"),
                )
            )
            dest.write_text(result.model_dump_json(indent=2), encoding="utf-8")
            print("Saved", len(result.action_items), "tasks", flush=True)


if __name__ == "__main__":
    main()
