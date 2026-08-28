"""Developer-only benchmark inspection without exposing truth by default."""

import argparse

from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.hidden_truth import load_hidden_truths
from resolveops.tools import default_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the fixed ResolveOps benchmark.")
    parser.add_argument("--show-truth", action="store_true", help="Print evaluator-only truth records.")
    args = parser.parse_args()
    cases = load_cases()
    truth_ids = {truth.case_id for truth in load_hidden_truths()}
    environment = default_environment()
    print(f"Benchmark cases: {len(cases)}")
    print(f"Each case has hidden truth: {all(case.case_id in truth_ids for case in cases)}")
    print("Observable cases:")
    for case in cases:
        device_type = environment.devices[case.primary_device_id].device_type if case.primary_device_id else "none"
        print(f"- {case.case_id}: {case.customer_id}, {case.primary_device_id}, {device_type}; {case.ticket_text}")
    if args.show_truth:
        print("\nEvaluator-only truth:")
        for truth in load_hidden_truths():
            print(truth.model_dump_json())


if __name__ == "__main__":
    main()
