"""Evaluator-only scoring command for completed baseline generation artifacts."""

import argparse
import json

from resolveops.agents.baseline.artifacts import ArtifactStore
from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.hidden_truth import load_hidden_truths
from resolveops.evaluation.models import CandidateOutput, RuntimeMetrics
from resolveops.evaluation.scoring import score_benchmark


def score_saved_run(run_id: str) -> None:
    store = ArtifactStore(run_id)
    candidates_path = store.result_dir / "candidates.json"
    runtime_path = store.result_dir / "runtime.json"
    if not candidates_path.exists() or not runtime_path.exists():
        raise FileNotFoundError(f"No completed baseline artifacts found for run: {run_id}")
    candidates = {
        case_id: CandidateOutput.model_validate(value)
        for case_id, value in json.loads(candidates_path.read_text(encoding="utf-8")).items()
    }
    runtime = {
        case_id: RuntimeRecord.model_validate(value).metrics
        for case_id, value in json.loads(runtime_path.read_text(encoding="utf-8")).items()
    }
    result = score_benchmark(load_cases(), load_hidden_truths(), candidates, runtime)
    ArtifactStore._write_json(store.result_dir / "score_summary.json", result.summary.model_dump(mode="json"))
    ArtifactStore._write_json(store.result_dir / "case_scores.json", [score.model_dump(mode="json") for score in result.case_scores])


def main() -> None:
    parser = argparse.ArgumentParser(description="Score an already-generated baseline run.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    score_saved_run(args.run_id)


if __name__ == "__main__":
    main()
