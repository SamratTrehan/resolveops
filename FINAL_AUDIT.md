# Final Audit

**Audit date:** 2026-08-29

- **Environment:** Python 3.12.10 virtual environment; `openai-agents==0.22.0`, `pydantic==2.13.5`, `streamlit==1.62.0`, and `pytest==9.1.1` match `requirements.txt`.
- **Reproducibility:** Python 3.12 setup, offline inspection, deterministic report generation, live-run configuration, scoring, Streamlit launch, and approval-demo paths are documented in the README. Dependencies are pinned; no dependency was added or upgraded.
- **Frozen historical integrity:** `baseline-official-004`, `resolveops-phase4-002`, and `resolveops-phase5a-001` exist and are readable. Their score summaries match the final comparison report: 10/15, 12/15, and 14/15 strict successes (66.67%, 80.00%, and 93.33% VRSR). Phase 5A has 100.00% required evidence-reference coverage and zero forbidden-claim violations. No frozen artifact was regenerated during this audit.
- **Secrets and data:** `.env`, virtual environments, caches, Python bytecode, and pytest temporary bases are ignored. The tracked configuration example contains only an empty API-key placeholder. No obvious credential or private customer-data value was found; IDs and cases are synthetic.
- **Public/demo boundary:** Streamlit and its read-only loader consume frozen comparison/trajectory artifacts only. The loader rejects evaluator-only fields and does not load hidden truth for normal presentation.
- **Demo status:** Streamlit imports successfully. The default Interactive Judge Simulation and Historical Replay resolve recorded Phase 5A cases without an API key; live inference is optional and requires only a server-side configured key. Human approval remains session-local and controls only simulated state-changing actions; it does not affect deterministic scoring.
- **Metric scope:** Required evidence-reference coverage checks required tool/source IDs in candidate references. It is not full semantic entailment or perfect claim-level citation verification. Verifier decisions and human approval are audited outside VRSR.
- **Cost disclosure:** Recorded runtime and token totals are available. Historical dollar cost is unavailable because persisted `model_cost_usd` values are null and no frozen pricing/accounting table supports defensible reconstruction.
- **Known limitation / Hot Take:** A different prompt does not make a same-model Verifier epistemically independent. In CASE-003, the Resolver's conservative abstention was reinforced rather than corrected; it remains the one final failure.
- **Evaluation provenance:** Frozen run IDs, source paths, hashes, and evaluation-contract commit `6c2571418069dc3a7d78fd0081bbd9cdc401e1b1` are recorded in README. Public Git history is not claimed as independent proof of private development chronology.
- **Manual submission tasks:** Record a video no longer than five minutes, confirm final working-tree cleanliness after any local demonstration, supply the repository URL, and complete the submission form.
