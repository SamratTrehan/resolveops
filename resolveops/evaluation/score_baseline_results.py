"""Evaluator-only scoring command for completed baseline generation artifacts."""

import argparse
import json
from pathlib import Path

from resolveops.agents.baseline.artifacts import ArtifactStore, RunManifest
from resolveops.agents.baseline.records import RuntimeRecord
from resolveops.evaluation.benchmark import load_cases
from resolveops.evaluation.hidden_truth import load_hidden_truths
from resolveops.evaluation.models import CandidateOutput, ExecutionFailure, RuntimeMetrics
from resolveops.evaluation.scoring import score_benchmark


def score_saved_run(run_id: str, root: Path | None = None) -> None:
    store = ArtifactStore(run_id, root=root)
    if (store.result_dir / "failure.json").exists():
        raise RuntimeError(f"Cannot score incomplete baseline run: {run_id}")
    candidates_path = store.result_dir / "candidates.json"
    runtime_path = store.result_dir / "runtime.json"
    manifest_path = store.result_dir / "manifest.json"
    failures_path = store.result_dir / "execution_failures.json"
    if not candidates_path.exists() or not runtime_path.exists() or not manifest_path.exists() or not failures_path.exists():
        raise FileNotFoundError(f"No completed baseline artifacts found for run: {run_id}")
    manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    if manifest.status != "completed":
        raise RuntimeError(f"Cannot score incomplete baseline run: {run_id}")
    if set(manifest.case_ids) != {case.case_id for case in load_cases()}:
        raise RuntimeError(f"Cannot score incomplete baseline run: {run_id}")
    candidates = {
        case_id: CandidateOutput.model_validate(value)
        for case_id, value in json.loads(candidates_path.read_text(encoding="utf-8")).items()
    }
    runtime = {
        case_id: RuntimeRecord.model_validate(value).metrics
        for case_id, value in json.loads(runtime_path.read_text(encoding="utf-8")).items()
    }
    execution_failures = {
        case_id: ExecutionFailure.model_validate(value)
        for case_id, value in json.loads(failures_path.read_text(encoding="utf-8")).items()
    }
    if set(candidates) | set(execution_failures) != set(manifest.case_ids):
        raise RuntimeError(f"Cannot score incomplete baseline run: {run_id}")
    result = score_benchmark(load_cases(), load_hidden_truths(), candidates, runtime, execution_failures)
    ArtifactStore._write_json(store.result_dir / "score_summary.json", result.summary.model_dump(mode="json"))
    ArtifactStore._write_json(store.result_dir / "case_scores.json", [score.model_dump(mode="json") for score in result.case_scores])


def main() -> None:
    parser = argparse.ArgumentParser(description="Score an already-generated baseline run.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    score_saved_run(args.run_id)


if __name__ == "__main__":
    main()
