"""One bundled TS3005d call using the SAME persistent quota ledger.

This diagnostic uses one model pass followed by local validation and manual
semantic review; it is not represented as an independent model-review pass.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import AnswerBatch, Budget
from verify_day08_live import verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.decision_tracking import INSTRUCTION as DI
from meeting_intelligence.decision_tracking import GeneratedDecisions, track_decisions
from meeting_intelligence.qa import INSTRUCTION as QI
from meeting_intelligence.qa import ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import Generation, build_payload, settings_from_environment
from meeting_intelligence.summary_schemas import StrictModel


class Combined(StrictModel):
    actions: GeneratedActions
    decisions: GeneratedDecisions
    qa: AnswerBatch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    root = a.environment_root
    output = root / "outputs/day08/completion_2026-11-20"
    budget = Budget(output, 20)
    settings = settings_from_environment(root)
    path = output / "TS3005d_revisions.result.json"
    result = json.loads(path.read_text())
    t = Transcript.model_validate(result["transcript"])
    questions = [
        "What is the final decision in this excerpt about the curve, speech recognition and scroll wheel?",
        "What is the confirmed bank account number for the project?",
    ]
    instruction = (
        "Analyze this meeting using the following rules for each field. Return only the Combined JSON schema. For QA return both indexed questions independently.\nACTIONS:\n"
        + ACTION_INSTRUCTION
        + "\nDECISIONS:\n"
        + DI
        + "\nQA:\n"
        + QI
    )
    payload = json.dumps(
        {
            "transcript": json.loads(build_payload(t)),
            "questions": [dict(question_index=i, question=q) for i, q in enumerate(questions)],
            "allowed_segment_ids": [s.id for s in t.segments],
            "review_requirements": "Copy IDs exactly including zeros. Review all later turns before final decisions. Exclude product-component inclusion/removal choices from action items unless distinct follow-up work is assigned. A rejected alternative is not withdrawal of a different accepted option: keep the accepted option as agreed and resolve the rejected alternative. For decisions phrased negatively, state the agreed exclusion, do not label exclusion of an unaccepted proposed feature as withdrawal of an established agreement. Never infer a real person from an anonymous speaker ID. Do not turn a price constraint into a new agreement. Do not guess any number from unclear ASR. Prefer a few well-supported topics over speculative entries.",
        }
    )
    raw = budget.generator(settings, Combined, instruction, 16384).generate(payload)
    generated = Combined.model_validate_json(raw.text)

    class Saved:
        def __init__(self, value):
            self.value = value

        def generate(self, payload):
            return Generation(self.value.model_dump_json(), raw.model_version, {})

    result["actions"] = extract_actions(t, settings.model, Saved(generated.actions)).model_dump(
        mode="json"
    )
    result["decisions"] = track_decisions(t, settings.model, Saved(generated.decisions)).model_dump(
        mode="json"
    )
    backup = output / "TS3005d_revisions.before_bundled.result.json"
    if not backup.exists():
        backup.write_bytes(path.read_bytes())
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    assert sorted(x.question_index for x in generated.qa.answers) == [0, 1]
    answers = []
    for i, q in enumerate(questions):
        item = next(x for x in generated.qa.answers if x.question_index == i)

        class SavedQA:
            def generate(self, payload):
                return Generation(
                    item.model_dump_json(exclude={"question_index"}), raw.model_version, {}
                )

        answers.append(ask(t, q, settings.model, SavedQA()).model_dump(mode="json"))
    checks = verify(result)
    for answer in answers:
        verify({"transcript": result["transcript"], "qa": answer})
    (output / "TS3005d_revisions.qa.json").write_text(
        json.dumps(
            dict(
                answers=answers,
                usage=raw.usage,
                note="One bundled real Gemini call; local validation plus manual semantic review required. No separate model review call.",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            dict(
                checks=checks,
                requests_attempted=len(budget.entries),
                status="ready_for_manual_semantic_review",
            )
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
