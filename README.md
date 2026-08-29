# ResolveOps

ResolveOps is an evidence-grounded, synthetic technical-support workflow for Tier-1 and Tier-2 agents. It investigates through deterministic tools, produces an evidence-backed resolution, checks it with a separate Verifier stage, and requires human approval before simulated state-changing actions.

All customers, devices, accounts, actions, and historical artifacts in this repository are synthetic. ResolveOps does not connect to real customer systems.

## Judge Quick Start

**No OpenAI API key is required to evaluate ResolveOps.** This path is **OFFLINE / ZERO API COST**. It opens the Streamlit presentation using frozen historical artifacts; it does not run an agent or require an API key.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run streamlit_app.py
```

macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py
```

The default **Interactive Judge Simulation** replays real recorded agent outputs for curated synthetic tickets, then applies only deterministic local safety interaction. **Historical Replay** is the direct, read-only trajectory view, including the CASE-003 known limitation. **Measured Improvement** shows the frozen baseline-to-final comparison. None of these paths loads evaluator-only truth or calls an API.

Open **Case Battle** to compare the frozen fair baseline and final ResolveOps architecture on the same support case. It is zero-API and derived only from immutable recorded artifacts.

## Final architecture

```text
Ticket
-> Investigator
-> Resolver
-> Verifier
-> optional one Resolver correction
-> Human Safety Gate
-> Resolution Packet
```

The fixed 15-case evaluation improved as follows, using the same synthetic cases, public output ontology, model family, and deterministic scoring contract:

| Stage | Strict successes | VRSR | Required evidence-reference coverage |
| --- | ---: | ---: | ---: |
| Baseline v2 | 10/15 | 66.67% | 73.33% |
| Investigator + Resolver | 12/15 | 80.00% | 93.33% |
| + Verifier + optional one correction | 14/15 | 93.33% | 100.00% |

Strict benchmark success requires:

- an accepted diagnosis or justified abstention;
- an accepted action;
- the correct escalation decision;
- required evidence-reference coverage; and
- no forbidden critical claim.

Verifier approval/rejection and Human Safety Gate approval are not part of this deterministic pass calculation; those behaviors are audited separately.

Required evidence-reference coverage means the required tool IDs and required source IDs appear in the candidate evidence references. It does not prove that every natural-language statement is semantically entailed, that every citation is perfectly attached to the correct claim, or that customer-facing prose has undergone complete semantic fact verification.

The reliability improvement carries a visible tradeoff: average recorded latency rose from 9,692.86 ms to 23,815.48 ms and recorded token use from 45,661 to 151,432. Investigator + Resolver primarily improved evidence discipline and strict conjunction-level success; diagnosis, action, and escalation each remained 86.67%. Adding verification/revision raised those three component metrics to 93.33% while required evidence-reference coverage reached 100%.

Recorded token usage is reported, but historical dollar cost is unavailable because the run artifacts did not persist the complete pricing/accounting data needed for a defensible reconstruction. Baseline retry usage may also be undercounted where usage was unavailable.

## Hot Take

A Verifier is not independent merely because it has a different prompt. CASE-003 remained the one final failure: the Resolver conservatively abstained, and the same-model Verifier reinforced that conservative bias instead of correcting it. Verification improved aggregate reliability, but this case shows that role separation alone does not guarantee epistemic independence when stages share the same model, evidence, and uncertainty assumptions.

## Reproducible setup

Python **3.12** is required. Create a local `.env` only for live runs:

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

`.env.example` contains placeholders only. Set these environment values for a live run:

```ini
OPENAI_API_KEY=
RESOLVEOPS_MODEL=gpt-5.6-terra
RESOLVEOPS_REASONING_EFFORT=medium
```

Supported reasoning efforts are `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. The selected model and effort are recorded in manifests, runtime records, and trajectories.

## Offline inspection and checks

These commands are **OFFLINE / ZERO API COST**:

```bash
python -m pytest
python -m resolveops.tools.demo
python -m resolveops.evaluation.inspect_benchmark
python -m resolveops.evaluation.report_experiments
```

The simulator demo prints deterministic synthetic evidence. Benchmark inspection prints observable case inputs only. `--show-truth` is a developer-only evaluator inspection option and is never used by agent runtime or the Streamlit demo. The report generator reads frozen score artifacts and writes only `evaluation/reports/final_comparison.json` and `.md`.

## Judge modes

| Mode | API key | New LLM inference | Purpose |
| --- | --- | --- | --- |
| Interactive Judge Simulation | No | No | Guided product exploration using recorded ResolveOps trajectories and deterministic synthetic safety behavior. |
| Historical Replay | No | No | Direct read-only inspection of immutable official trajectories. |
| Live ResolveOps | Yes | Yes | Fresh inference from a new explicit CLI run ID. |

The simulation maps service outage, local Wi-Fi, camera/device, insufficient-evidence, and approval-required provisioning scenarios to recorded Phase 5A cases. Safety decisions are temporary Streamlit session state; they never write trajectories, benchmark artifacts, reports, or synthetic source data.

## Historical artifacts and scoring

The frozen, comparable runs are retained read-only:

- `baseline-official-004` — Baseline v2
- `resolveops-phase4-002` — Investigator + Resolver
- `resolveops-phase5a-001` — Investigator + Resolver + Verifier + optional revision

Score a newly generated artifact set after its live runner has completed:

```bash
python -m resolveops.evaluation.score_baseline_results --run-id baseline-new
python -m resolveops.evaluation.score_resolveops_results --run-id resolveops-new
```

These scoring commands load evaluator-only truth and rewrite only the selected run's deterministic score outputs. They are for evaluation maintenance, not the public Judge Demo. Do not run them against the frozen historical runs unless an intentional artifact refresh is required.

## Evaluation provenance

- Fair baseline: `evaluation/results/baseline/baseline-official-004/`
- Investigator + Resolver: `evaluation/results/resolveops/resolveops-phase4-002/`
- Final ResolveOps: `evaluation/results/resolveops/resolveops-phase5a-001/`
- Observable benchmark: `data/cases/benchmark_cases.json` — SHA-256 `D3D39414450AC092075D7C7C75FF393D525B7E0CF3D315BA49030343217E6102`
- Evaluator-only truth: `resolveops/evaluation/data/benchmark_truth.json` — SHA-256 `4D27B663A7F83FAF9C000767167325D6F09198D732ECF76E16EB648C2A5157A5`
- Deterministic scorer: `resolveops/evaluation/scoring.py` — SHA-256 `BBED96EE8EB74049AB266205C33812883ACF9BB657DACE997260A4BE34D49F2F`
- Public ontology: `resolveops/domain/support_ontology.py` — SHA-256 `1AE71D7B56A703DD9632382EA4AA809318DE13050CC115431E2590DD329F0E97`
- Final comparison: `evaluation/reports/final_comparison.json` and `.md`
- Final fair evaluation-contract commit: `6c2571418069dc3a7d78fd0081bbd9cdc401e1b1` (`phase-3d-public-support-ontology`)

Project chronology records the benchmark cases during local/private development before the agent workflow was implemented. The initial public Git import and subsequent public history do not independently prove that private chronology, so this repository does not claim that Git history alone establishes benchmark pre-registration.

## Live agent execution and benchmark reruns

The following commands are **LIVE / CONSUMES OPENAI API TOKENS**. They require `OPENAI_API_KEY`, use the configured model/effort, and create a new explicit run ID. Existing IDs are rejected without overwrite. Re-running a model-based benchmark is optional and is never needed for the judge simulation or historical replay.

```bash
python -m resolveops.agents.baseline.runner --case-id CASE-001 --run-id baseline-smoke-new
python -m resolveops.agents.baseline.runner --all --run-id baseline-new --official
python -m resolveops.evaluation.score_baseline_results --run-id baseline-new

python -m resolveops.agents.resolveops.runner --case-id CASE-001 --run-id resolveops-smoke-new
python -m resolveops.agents.resolveops.runner --all --run-id resolveops-new
python -m resolveops.evaluation.score_resolveops_results --run-id resolveops-new
```

The baseline is one tool-using agent. ResolveOps separates evidence collection, resolution, and verification roles. A case receives at most one retry only for malformed structured output; valid-but-wrong reasoning is never retried. Execution failures remain in the full benchmark denominator.

## Human approval demonstration

The Streamlit historical playback is **OFFLINE / ZERO API COST**. In **Judge Demo**, select a recorded resolution whose action requires approval; the Safety Gate shows that simulated gateway activation is blocked pending an explicit human decision. Approving or rejecting it changes only the displayed synthetic safety record—never a real system, candidate, or score.

## Public output contract and safety

The public, case-agnostic root-cause and action ontology lives in `resolveops/domain/support_ontology.py`. It standardizes output labels without revealing case-specific answers. Hidden truth, accepted evaluator sets, and forbidden evaluator claims remain outside agent runtime and normal demo presentation.

Consequential simulation is deliberately separate from resolution quality: approval metadata does not alter `CandidateOutput` or VRSR scoring. ResolveOps does not claim 93% accuracy across general technical support. It demonstrates 14/15 strict successes on a frozen benchmark of 15 synthetic cases spanning repeated scenario families in a controlled world with a closed public ontology; CASE-003 remains the retained failure.

See [PROJECT_SPEC.md](PROJECT_SPEC.md), [TRAJECTORIES.md](TRAJECTORIES.md), [IMPROVEMENT_CHANGELOG.md](IMPROVEMENT_CHANGELOG.md), [FINAL_AUDIT.md](FINAL_AUDIT.md), and [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for the project record and submission status.
