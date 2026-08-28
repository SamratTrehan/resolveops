from resolveops.evaluation.report_experiments import build_report


def test_experiment_report_reads_historical_artifacts() -> None:
    report = build_report()
    runs = report["runs"]
    assert [item["run_id"] for item in runs] == ["baseline-official-004", "resolveops-phase4-002", "resolveops-phase5a-001"]
    assert runs[0]["vrsr_percent"] == 66.66666666666667
    assert report["deltas"][0]["vrsr_percentage_points"] > 0
    assert runs[0]["quality_revisions"] == 0 and runs[2]["quality_revisions"] == 4
