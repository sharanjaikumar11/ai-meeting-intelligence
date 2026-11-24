"""Run the real local app with the final validation's shared API budget."""

import argparse
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_day08_budgeted import Budget

from meeting_intelligence import web
from meeting_intelligence.summarization import SYSTEM_INSTRUCTION
from meeting_intelligence.summary_schemas import GeneratedNotes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--environment-root", type=Path, required=True)
    p.add_argument("--port", type=int, default=8001)
    p.add_argument(
        "--budget-folder", type=Path, help="Existing shared daily request ledger directory."
    )
    a = p.parse_args()
    budget = Budget(a.budget_folder or a.environment_root / "outputs/day10/final_2026-11-23", 20)

    def generator(
        settings, schema=GeneratedNotes, instruction=SYSTEM_INSTRUCTION, max_output_tokens=8192
    ):
        return budget.generator(settings, schema, instruction, max_output_tokens)

    web.GeminiGenerator = generator
    uvicorn.run(web.create_app(a.environment_root), host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
