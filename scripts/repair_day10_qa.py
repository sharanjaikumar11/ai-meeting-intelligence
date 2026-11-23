"""One budgeted schema repair for the saved development QA batch, no gold in request."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import AnswerBatch, Budget
from verify_day08_live import verify

from meeting_intelligence.qa import INSTRUCTION, ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import Generation, build_payload, settings_from_environment


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    a = p.parse_args()
    out = a.environment_root / "outputs/day10/improvement_2026-11-22"
    dest = out / "IS1003b_1458_1614.qa.json"
    if dest.exists():
        print("Saved repaired answers already exist.")
        return
    budget = Budget(out, 6)
    settings = settings_from_environment(a.environment_root)
    entries = json.loads((out / "request_ledger.json").read_text())
    invalid = json.loads((out / "calls" / f"{entries[4]['key']}.json").read_text())["text"]
    t = Transcript.model_validate_json(
        (a.environment_root / "outputs/day09/IS1003b_1458_1614.transcript.json").read_text()
    )
    queries = [
        "What should the Industrial Designer and User Interface Designer work on next?",
        "Was an entirely yellow remote finally selected?",
    ]
    payload = json.dumps(
        dict(
            task="Correct the schema error: not_found MUST have empty claims. When supported claims exist use answered or partial; when only part of a requested assignment is clear use partial. Keep only transcript-supported facts. Do not invent facts to repair the schema. Return exactly indices 0 and 1.",
            invalid_candidate=invalid,
            questions=[dict(question_index=i, question=q) for i, q in enumerate(queries)],
            transcript=json.loads(build_payload(t)),
        )
    )
    value = budget.generator(settings, AnswerBatch, INSTRUCTION).generate(payload)
    batch = AnswerBatch.model_validate_json(value.text)
    if sorted(i.question_index for i in batch.answers) != [0, 1]:
        raise ValueError("Wrong indices")
    answers = []
    for i, q in enumerate(queries):
        item = next(x for x in batch.answers if x.question_index == i)

        class Saved:
            def generate(self, payload):
                return Generation(
                    item.model_dump_json(exclude={"question_index"}), value.model_version, {}
                )

        answer = ask(t, q, settings.model, Saved()).model_dump(mode="json")
        verify(dict(transcript=t.model_dump(mode="json"), qa=answer))
        answers.append(answer)
    dest.write_text(
        json.dumps(
            dict(
                answers=answers,
                repair_usage=value.usage,
                note="Draft/review plus one schema repair; all attempts retained in ledger.",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    print("QA repair saved within six-attempt cap.")


if __name__ == "__main__":
    main()
