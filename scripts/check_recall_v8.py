"""Development checks on known failures; replay is not a new model generation."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import Budget
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import Generation, settings_from_environment


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    base = a.environment_root / "outputs/day10/final_2026-11-23"
    out = a.environment_root / "outputs/day10/recall_v8"
    out.mkdir(parents=True, exist_ok=True)
    ledger = json.loads((base / "request_ledger.json").read_text(encoding="utf-8"))
    saved = [
        json.loads((base / "calls" / (ledger[i]["key"] + ".json")).read_text(encoding="utf-8"))
        for i in [12, 13]
    ]

    class Replay:
        def __init__(self):
            self.calls = 0

        def generate(self, payload):
            value = saved[self.calls]
            self.calls += 1
            return Generation(value["text"], value["model_version"], {})

    t = Transcript.model_validate_json(
        (base / "TS3006a_0807_1000.transcript.json").read_text(encoding="utf-8")
    )
    replay = extract_actions(t, "cached-v7-candidate-local-v8-validation", Replay())
    verify(dict(transcript=t.model_dump(mode="json"), actions=replay.model_dump(mode="json")))
    (out / "TS3006a.replay.actions.json").write_text(
        replay.model_dump_json(indent=2), encoding="utf-8"
    )
    print(
        "Cached-candidate replay delivered",
        len(replay.action_items),
        "tasks; not new inference.",
        flush=True,
    )
    dest = out / "ES2006a.live.actions.json"
    if not dest.exists():
        settings = settings_from_environment(a.environment_root)
        budget = Budget(base, 20)
        t = Transcript.model_validate_json(
            (base / "ES2006a_1235_1275.transcript.json").read_text(encoding="utf-8")
        )
        result = extract_actions(
            t, settings.model, budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION)
        )
        verify(dict(transcript=t.model_dump(mode="json"), actions=result.model_dump(mode="json")))
        dest.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(dest.read_text(encoding="utf-8"), flush=True)


if __name__ == "__main__":
    main()
