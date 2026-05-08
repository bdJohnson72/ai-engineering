"""Run all test cases through the agent and dump output for manual review.

Usage:
    uv run python -m soto_agent.evals.run_evals
    uv run python -m soto_agent.evals.run_evals --model deepseek-r1

Writes a timestamped Markdown report to soto_agent/evals/runs/. Filename
includes the model name so multi-model comparisons stay sortable.

Manual review is intentional for v1 — a small N benefits more from human
eyes than from an LLM judge. Once the eval set crosses ~20 cases, consider
adding LLM-as-judge for grading must_use_terms / must_not_do constraints.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from soto_agent.app import DEFAULT_MODEL, run_agent

EVALS_DIR = Path(__file__).parent
TEST_CASES_PATH = EVALS_DIR / "test_cases.jsonl"
RUNS_DIR = EVALS_DIR / "runs"


def load_cases() -> list[dict]:
    with open(TEST_CASES_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=None,
        help=f"Model name; default {DEFAULT_MODEL} from SOTO_MODEL env.",
    )
    args = parser.parse_args()
    model_name = args.model or DEFAULT_MODEL

    cases = load_cases()
    print(f"Loaded {len(cases)} test cases. Model: {model_name}\n")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    RUNS_DIR.mkdir(exist_ok=True)
    out_path = RUNS_DIR / f"{timestamp}-{model_name}.md"

    with open(out_path, "w") as out:
        out.write(f"# Eval run — {timestamp}\n\n")
        out.write(f"- **Model:** `{model_name}`\n")
        out.write(f"- **Total cases:** {len(cases)}\n\n---\n\n")

        for i, case in enumerate(cases, 1):
            print(f"[{i}/{len(cases)}] {case['id']} ({case['category']})")
            print(f"   Q: {case['question']}")

            t0 = time.perf_counter()
            try:
                answer = run_agent(case["question"], model=model_name)
                error = None
            except Exception as e:
                answer = ""
                error = f"{type(e).__name__}: {e}"
            dt = time.perf_counter() - t0

            print(f"   ({dt:.1f}s, {len(answer)} chars){' ERROR' if error else ''}")

            out.write(f"## {case['id']}\n\n")
            out.write(f"- **Category:** {case['category']}\n")
            out.write(f"- **Latency:** {dt:.1f}s\n")
            out.write(f"- **Question:** {case['question']}\n")
            out.write(f"- **Expected behavior:** {case['expected_behavior']}\n")
            if case.get("must_use_terms"):
                out.write(f"- **Must use terms:** {', '.join(case['must_use_terms'])}\n")
            if case.get("must_not_do"):
                out.write(f"- **Must not do:** {', '.join(case['must_not_do'])}\n")
            if case.get("notes"):
                out.write(f"- **Notes:** {case['notes']}\n")
            out.write("\n### Answer\n\n")
            if error:
                out.write(f"**ERROR:** `{error}`\n\n")
            else:
                out.write(f"{answer}\n\n")
            out.write("### Manual review\n\n")
            out.write("- [ ] Pass\n- [ ] Fail\n- Notes:\n\n---\n\n")

    print(f"\nWrote report: {out_path}")


if __name__ == "__main__":
    main()
