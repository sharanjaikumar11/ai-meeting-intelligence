"""Sequential, cached Day 8 checks with a persistent cap on actual SDK calls.

The cap covers this script only, not other clients using the same Google project.
No automatic SDK retries. Existing validated stages are reused. Original results
are retained; revised outputs are written to a separate review directory.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from pydantic import Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from verify_day08_live import CASES, verify

from meeting_intelligence.action_extraction import ACTION_INSTRUCTION, extract_actions
from meeting_intelligence.action_schemas import GeneratedActions
from meeting_intelligence.decision_tracking import INSTRUCTION as DECISION_INSTRUCTION
from meeting_intelligence.decision_tracking import (
    DecisionReviewGenerator,
    GeneratedDecisions,
    track_decisions,
)
from meeting_intelligence.pipeline import transcription_quality_warnings
from meeting_intelligence.qa import INSTRUCTION as QA_INSTRUCTION
from meeting_intelligence.qa import GeneratedAnswer, ask
from meeting_intelligence.schemas import Transcript
from meeting_intelligence.summarization import (
    SYSTEM_INSTRUCTION,
    GeminiGenerator,
    Generation,
    SummaryError,
    build_payload,
    settings_from_environment,
    summarize,
)
from meeting_intelligence.summary_schemas import GeneratedNotes, StrictModel


class IndexedAnswer(GeneratedAnswer):
    question_index: int


class AnswerBatch(StrictModel):
    answers: list[IndexedAnswer] = Field(min_length=1, max_length=2)


class Budget:
    def __init__(self, folder, limit):
        self.folder = folder
        self.limit = limit
        self.path = folder / "request_ledger.json"
        self.entries = json.loads(self.path.read_text()) if self.path.exists() else []

    def generator(self, settings, schema, instruction, tokens=8192):
        parent = self
        base = GeminiGenerator(
            settings,
            schema=schema,
            instruction=instruction,
            max_output_tokens=tokens,
            retry_attempts=1,
            request_timeout_ms=120000,
        )

        class Cached:
            def generate(self, payload):
                key = hashlib.sha256(
                    json.dumps(
                        [settings.model, schema.model_json_schema(), instruction, payload, tokens],
                        sort_keys=True,
                    ).encode()
                ).hexdigest()
                path = parent.folder / "calls" / f"{key}.json"
                path.parent.mkdir(exist_ok=True)
                if path.exists():
                    return Generation(**json.loads(path.read_text()))
                if len(parent.entries) >= parent.limit:
                    raise SummaryError("Local request budget reached; saved results are preserved.")
                if parent.entries:
                    delay = 16 - (time.time() - parent.entries[-1]["started_unix"])
                    if delay > 0:
                        time.sleep(delay)
                entry = dict(
                    number=len(parent.entries) + 1,
                    started_unix=time.time(),
                    key=key,
                    status="started",
                )
                parent.entries.append(entry)
                parent.save()
                print(
                    f"Gemini request {len(parent.entries)}/{parent.limit}: {schema.__name__}",
                    flush=True,
                )
                try:
                    value = base.generate(payload)
                    path.write_text(
                        json.dumps(
                            dict(
                                text=value.text,
                                model_version=value.model_version,
                                usage=value.usage,
                            )
                        ),
                        encoding="utf-8",
                    )
                    entry["status"] = "completed"
                    parent.save()
                    return value
                except Exception as exc:
                    entry["status"] = "failed"
                    entry["error"] = (
                        str(exc) if isinstance(exc, SummaryError) else type(exc).__name__
                    )
                    parent.save()
                    raise

        return Cached()

    def save(self):
        self.path.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")


def questions(t, queries, settings, budget):
    instruction = (
        QA_INSTRUCTION
        + "\nAnswer each indexed question independently in the answers array. Return exactly one answer per question_index. Do not merge separate questions."
    )
    generator = budget.generator(settings, AnswerBatch, instruction)
    payload = json.dumps(
        {
            "questions": [dict(question_index=i, question=q) for i, q in enumerate(queries)],
            "transcript": json.loads(build_payload(t)),
        }
    )
    draft = generator.generate(payload)
    reviewed = generator.generate(
        json.dumps(
            {
                "task": "Review every answer independently against the original transcript. Correct unsupported ownership, preserve unresolved choices, use partial for missing requested fields, and abstain on unsupported questions. Return the complete indexed answers array.",
                "source_request": json.loads(payload),
                "candidate": draft.text,
            }
        )
    )
    batch = AnswerBatch.model_validate_json(reviewed.text)
    assert sorted(a.question_index for a in batch.answers) == list(range(len(queries)))
    result = []
    for i, q in enumerate(queries):
        item = next(a for a in batch.answers if a.question_index == i)

        class Saved:
            def generate(self, payload):
                return Generation(
                    item.model_dump_json(exclude={"question_index"}), reviewed.model_version, {}
                )

        result.append(ask(t, q, settings.model, Saved()).model_dump(mode="json"))
    return dict(
        answers=result,
        usage={
            k: draft.usage.get(k, 0) + reviewed.usage.get(k, 0)
            for k in draft.usage.keys() | reviewed.usage.keys()
        },
        note="Questions batched for quota efficiency; draft + model review. Each answer validated with the application QA validator.",
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--run-label", default="completion_2026-11-20")
    p.add_argument("--limit", type=int, default=20)
    a = p.parse_args()
    root = a.environment_root
    output = root / "outputs/day08" / a.run_label
    output.mkdir(exist_ok=True)
    budget = Budget(output, a.limit)
    settings = settings_from_environment(root)
    report_path = output / "run.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {}

    def save():
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    for name, _, _, _, question in CASES:
        path = output / f"{name}.result.json"
        if path.exists():
            result = json.loads(path.read_text())
        else:
            old = json.loads((root / "outputs/day08" / f"{name}.json").read_text())
            previous = json.loads(
                (root / "outputs/web" / old["meeting_id"] / "result.json").read_text()
            )
            result = {k: previous[k] for k in ["transcript", "summary"] if k in previous}
        t = Transcript.model_validate(result["transcript"])
        tasks = [
            (
                "summary",
                lambda: summarize(
                    t,
                    settings.model,
                    budget.generator(settings, GeneratedNotes, SYSTEM_INSTRUCTION),
                ),
            ),
            (
                "actions",
                lambda: extract_actions(
                    t,
                    settings.model,
                    budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION),
                ),
            ),
            (
                "decisions",
                lambda: track_decisions(
                    t,
                    settings.model,
                    DecisionReviewGenerator(
                        budget.generator(settings, GeneratedDecisions, DECISION_INSTRUCTION, 16384)
                    ),
                ),
            ),
        ]
        for key, fn in tasks:
            if key not in result:
                print(name, key, flush=True)
                result[key] = fn().model_dump(mode="json")
                path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        report[name] = dict(checks=verify(result), status="extraction_complete")
        save()
        qpath = output / f"{name}.qa.json"
        if not qpath.exists():
            queries = [question]
            if name != "ES2005a_full":
                queries.append("What is the confirmed bank account number for the project?")
            qa = questions(t, queries, settings, budget)
            qpath.write_text(json.dumps(qa, indent=2), encoding="utf-8")
        else:
            qa = json.loads(qpath.read_text())
        report[name]["qa_evidence"] = [
            verify({"transcript": result["transcript"], "qa": answer})["verified_evidence"]
            for answer in qa["answers"]
        ]
        if len(qa["answers"]) > 1:
            assert qa["answers"][1]["status"] == "not_found"
            report[name]["abstention_passed"] = True
        report[name]["status"] = "ready_for_semantic_review"
        save()
        print(name, "ready for semantic review", flush=True)
    # A degraded-transcript downstream check, explicitly separate from the clean meetings.
    t = Transcript.model_validate_json(
        (root / "outputs/day08/local_noisy_5db.transcript.json").read_text()
    )
    t = t.model_copy(update={"warnings": t.warnings + transcription_quality_warnings(t.segments)})
    path = output / "noisy_actions.json"
    try:
        build_payload(t)
    except SummaryError as exc:
        if "Transcript needs audio review" not in str(exc):
            raise
        report["noisy_actions"] = dict(
            status="blocked_for_audio_review",
            quality_gate_passed=True,
            message=str(exc),
            gemini_requests=0,
        )
    else:
        if not path.exists():
            value = extract_actions(
                t, settings.model, budget.generator(settings, GeneratedActions, ACTION_INSTRUCTION)
            )
            path.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        report["noisy_actions"] = dict(
            checks=verify(
                {"transcript": t.model_dump(mode="json"), "actions": json.loads(path.read_text())}
            ),
            status="ready_for_semantic_review",
        )
    report["requests_attempted"] = len(budget.entries)
    save()
    print("Budgeted run finished:", len(budget.entries), "requests", flush=True)


if __name__ == "__main__":
    main()
