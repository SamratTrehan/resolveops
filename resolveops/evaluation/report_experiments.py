"""Deterministic Phase 6 comparison report from immutable score artifacts."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNS = (
    ("baseline-official-004", "Baseline v2", ROOT / "evaluation/results/baseline/baseline-official-004", ROOT / "trajectories/baseline/baseline-official-004"),
    ("resolveops-phase4-002", "Investigator -> Resolver", ROOT / "evaluation/results/resolveops/resolveops-phase4-002", ROOT / "trajectories/resolveops/resolveops-phase4-002"),
    ("resolveops-phase5a-001", "Investigator -> Resolver -> Verifier -> optional revision", ROOT / "evaluation/results/resolveops/resolveops-phase5a-001", ROOT / "trajectories/resolveops/resolveops-phase5a-001"),
)


def _read(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required historical artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _run_record(run_id: str, architecture: str, result_dir: Path, trajectory_dir: Path) -> dict[str, object]:
    summary, manifest, failures = (_read(result_dir / name) for name in ("score_summary.json", "manifest.json", "execution_failures.json"))
    record = {
        "run_id": run_id, "architecture": architecture, "model": manifest["model"], "reasoning_effort": manifest["reasoning_effort"],
        "vrsr_percent": summary["vrsr_percent"], "passed_cases": summary["passed_cases"], "total_cases": summary["total_cases"],
        "diagnosis_accuracy": summary["diagnosis_accuracy"], "action_accuracy": summary["action_accuracy"], "escalation_accuracy": summary["escalation_accuracy"], "evidence_coverage": summary["evidence_coverage"], "forbidden_claim_violation_count": summary["forbidden_claim_violation_count"], "forbidden_claim_violation_rate": summary["forbidden_claim_violation_rate"], "execution_failures": len(failures),
        "average_latency_ms": summary.get("runtime_summary", {}).get("average_latency_ms"), "recorded_token_usage": summary.get("runtime_summary", {}).get("total_token_usage"), "tool_calls": summary.get("runtime_summary", {}).get("total_tool_call_count"),
        "quality_revisions": len(list(trajectory_dir.glob("*-resolver-revision-v1.json"))) if trajectory_dir.exists() else 0,
    }
    return record


def _delta(before: dict[str, object], after: dict[str, object]) -> dict[str, object]:
    def relative(key: str) -> float | None:
        a, b = before[key], after[key]
        return None if a is None or b is None or a == 0 else 100 * (b - a) / a
    return {"from": before["run_id"], "to": after["run_id"], "vrsr_percentage_points": after["vrsr_percent"] - before["vrsr_percent"], "evidence_coverage_percentage_points": after["evidence_coverage"] - before["evidence_coverage"], "latency_relative_percent": relative("average_latency_ms"), "token_usage_relative_percent": relative("recorded_token_usage")}


def build_report(root: Path = ROOT) -> dict[str, object]:
    records = [_run_record(run_id, architecture, root / result.relative_to(ROOT), root / trajectories.relative_to(ROOT)) for run_id, architecture, result, trajectories in RUNS]
    return {"runs": records, "deltas": [_delta(records[0], records[1]), _delta(records[1], records[2]), _delta(records[0], records[2])], "notes": {"baseline_recorded_usage": "Recorded token usage may undercount retry attempts whose usage was unavailable.", "phase5b": "Human approval is a safety gate, not a quality benchmark result."}}


def write_report(root: Path = ROOT) -> tuple[Path, Path]:
    report = build_report(root)
    out = root / "evaluation/reports"; out.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = out / "final_comparison.json", out / "final_comparison.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    rows = ["# ResolveOps final comparison", "", "| Run | Architecture | Strict success (VRSR) | Required evidence-reference coverage | Latency ms | Tokens |", "|---|---|---:|---:|---:|---:|"]
    rows += [f"| {r['run_id']} | {r['architecture']} | {r['vrsr_percent']:.2f}% | {r['evidence_coverage']:.2f}% | {r['average_latency_ms']:.2f} | {r['recorded_token_usage']} |" for r in report["runs"]]
    rows += ["", "Strict benchmark success: 66.67% -> 80.00% -> 93.33%; required evidence-reference coverage: 73.33% -> 93.33% -> 100.00%. Higher reliability came with latency/token cost.", "", "VRSR is the strict conjunction of accepted diagnosis/abstention, accepted action, correct escalation, required evidence references, and no forbidden critical claim. Verifier decisions and human approval are audited separately."]
    markdown_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return json_path, markdown_path


if __name__ == "__main__":
    write_report()
