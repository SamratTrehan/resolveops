"""Non-overwriting local artifact storage for baseline generation runs."""

import json
import re
from pathlib import Path

from pydantic import BaseModel

from resolveops.agents.baseline.records import BaselineTrajectory, RuntimeRecord
from resolveops.evaluation.models import CandidateOutput, ExecutionFailure


RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class RunManifest(BaseModel):
    status: str = "completed"
    run_id: str
    run_kind: str
    model: str
    reasoning_effort: str
    agent_name: str
    prompt_id: str
    case_ids: list[str]
    successful_candidate_count: int = 0
    execution_failure_count: int = 0


class FailedRunRecord(BaseModel):
    status: str = "failed"
    run_id: str
    run_kind: str
    model: str
    reasoning_effort: str
    agent_name: str
    prompt_id: str
    requested_case_ids: list[str]
    completed_case_ids: list[str]
    failed_case_id: str
    error_type: str
    error_message: str


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


class ArtifactStore:
    def __init__(self, run_id: str, root: Path | None = None) -> None:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError("run_id must use lowercase letters, digits, hyphens, or underscores.")
        base = root or repository_root()
        self.run_id = run_id
        self.result_dir = base / "evaluation" / "results" / "baseline" / run_id
        self.trajectory_dir = base / "trajectories" / "baseline" / run_id

    def prepare(self) -> None:
        if self.result_dir.exists() or self.trajectory_dir.exists():
            raise FileExistsError(f"Baseline run already exists: {self.run_id}")
        self.result_dir.mkdir(parents=True)
        self.trajectory_dir.mkdir(parents=True)

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")

    def write_trajectory(self, trajectory: BaselineTrajectory) -> None:
        self._write_json(
            self.trajectory_dir / f"{trajectory.case_id}.json",
            trajectory.model_dump(mode="json"),
        )

    def write_results(
        self,
        candidates: dict[str, CandidateOutput],
        runtime_metadata: dict[str, RuntimeRecord],
        execution_failures: dict[str, ExecutionFailure],
        manifest: RunManifest,
    ) -> None:
        self._write_json(
            self.result_dir / "candidates.json",
            {case_id: candidate.model_dump(mode="json") for case_id, candidate in candidates.items()},
        )
        self._write_json(
            self.result_dir / "runtime.json",
            {case_id: record.model_dump(mode="json") for case_id, record in runtime_metadata.items()},
        )
        self._write_json(
            self.result_dir / "execution_failures.json",
            {case_id: failure.model_dump(mode="json") for case_id, failure in execution_failures.items()},
        )
        self._write_json(self.result_dir / "manifest.json", manifest.model_dump(mode="json"))

    def write_failure(
        self,
        candidates: dict[str, CandidateOutput],
        runtime_metadata: dict[str, RuntimeRecord],
        failure: FailedRunRecord,
    ) -> None:
        """Persist partial output without making the run appear scoreable."""
        self._write_json(
            self.result_dir / "candidates.json",
            {case_id: candidate.model_dump(mode="json") for case_id, candidate in candidates.items()},
        )
        self._write_json(
            self.result_dir / "runtime.json",
            {case_id: record.model_dump(mode="json") for case_id, record in runtime_metadata.items()},
        )
        self._write_json(self.result_dir / "failure.json", failure.model_dump(mode="json"))
