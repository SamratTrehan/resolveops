import json
from pathlib import Path

from resolveops.evaluation.report_experiments import build_report


ROOT = Path(__file__).resolve().parents[1]
FROZEN_RUNS = (
    ("baseline", "baseline-official-004", 66.66666666666667, 73.33333333333333),
    ("resolveops", "resolveops-phase4-002", 80.0, 93.33333333333333),
    ("resolveops", "resolveops-phase5a-001", 93.33333333333333, 100.0),
)


def test_frozen_score_summaries_match_the_offline_comparison_report() -> None:
    report = build_report(ROOT)
    by_id = {record["run_id"]: record for record in report["runs"]}

    for namespace, run_id, expected_vrsr, expected_evidence in FROZEN_RUNS:
        summary_path = ROOT / "evaluation" / "results" / namespace / run_id / "score_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["vrsr_percent"] == expected_vrsr
        assert summary["evidence_coverage"] == expected_evidence
        assert by_id[run_id]["vrsr_percent"] == summary["vrsr_percent"]
        assert by_id[run_id]["evidence_coverage"] == summary["evidence_coverage"]

    phase5a = json.loads((ROOT / "evaluation/results/resolveops/resolveops-phase5a-001/score_summary.json").read_text(encoding="utf-8"))
    assert phase5a["forbidden_claim_violation_count"] == 0
