# ResolveOps Submission Checklist

Use this checklist for the final manual handoff. Checked items are repository-audited; video, URL, and form fields remain manual tasks.

- [x] Source code is present.
- [x] README includes setup, offline Judge Quick Start, live-run boundaries, and final architecture.
- [x] Improvement changelog records the measured iterations.
- [x] Reproduction commands were verified in the Python 3.12 virtual environment.
- [x] Fixed benchmark and frozen evaluation artifacts are present.
- [x] `evaluation/reports/final_comparison.{json,md}` is present and matches frozen score summaries.
- [x] Evaluation provenance, metric definitions, exclusions, and artifact hashes are documented.
- [x] Representative trajectories are present and documented in `TRAJECTORIES.md`.
- [x] Full judge-facing simulation, historical replay, measured improvement, and human-approval safety work without an API key.
- [x] Repository data is synthetic and public-safe.
- [x] No credentials or private customer data were found in tracked project content.
- [x] Normal Streamlit/demo loaders reject evaluator-only fields and do not load hidden truth.
- [x] Simulation is visibly labeled as recorded/deterministic and live inference remains optional; no judge credential entry is requested.
- [x] Judge-facing claims use 14/15 strict benchmark success and required evidence-reference coverage rather than general-support accuracy claims.
- [x] Offline tests, package check, compilation, and diff whitespace check pass.
- [x] Streamlit imports and its historical artifact loaders resolve.
- [ ] Record a demonstration video of five minutes or less.
- [ ] Confirm the final repository is clean after any local demo/test session.
- [ ] Add the repository URL: ____________________
- [ ] Complete required submission-form fields manually: ____________________
