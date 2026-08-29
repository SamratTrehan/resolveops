# ResolveOps

ResolveOps is an evidence-grounded, synthetic technical-support workflow for Tier-1 and Tier-2 agents. It investigates through deterministic tools, produces an evidence-backed resolution, checks it with a separate Verifier stage, and requires human approval before simulated state-changing actions.

All customers, devices, accounts, actions, and historical artifacts in this repository are synthetic. ResolveOps does not connect to real customer systems.

## Judge Quick Start

**No OpenAI API key is required to evaluate ResolveOps.** This path is **OFFLINE / ZERO API COST**. It opens the Streamlit presentation using frozen historical artifacts; it does not run an agent or require an API key.

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run streamlit_app.py
```

macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run streamlit_app.py
```

The default **Interactive Judge Simulation** replays real recorded agent outputs for curated synthetic tickets, then applies only deterministic local safety interaction. **Historical Replay** is the direct, read-only trajectory view, including the CASE-003 known limitation. **Measured Improvement** shows the frozen baseline-to-final comparison. None of these recorded paths loads evaluator-only truth or calls an API.

Open **Case Battle** to compare the frozen fair baseline and final ResolveOps architecture on the same support case. It is zero-API and derived only from immutable recorded artifacts.

## Judge Challenge — Fresh Inference

Judge Challenge performs up to three new ResolveOps inferences per Streamlit session using judge-selected observable synthetic cases. The judge may rewrite each ticket symptom, while the template's synthetic customer and device IDs remain fixed. It reuses the production Investigator → Resolver → Verifier → optional one revision → Safety Gate workflow entirely in memory.

Fresh demonstration runs are not benchmark-scored and never update official metrics, frozen trajectories, evaluation artifacts, or hidden truth. The server-side OpenAI credential is never displayed, written to session state, or requested through the UI. If fresh inference is unavailable, Interactive Judge Simulation, Historical Replay, Case Battle, and Measured Improvement remain fully usable.

The up-to-three-run allowance is a Streamlit-session usage budget, not a security-grade global rate limiter. A browser refresh or new session may reset it.

For Streamlit Cloud, set the maintainer-only secret under **App settings → Secrets** using top-level TOML syntax:

```toml
OPENAI_API_KEY = "..."
```

For local development, the environment-variable fallback remains supported. A placeholder is provided in `.streamlit/secrets.toml.example`; copy it to `.streamlit/secrets.toml` and add a real value only on your machine. `.streamlit/secrets.toml` and `.env` are ignored and must never be committed.

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

| Stage | Strict benchmark successes (VRSR) | Required evidence-reference coverage |
| --- | ---: | ---: |
| Baseline | 10/15 (66.67%) | 73.33% |
| Investigator + Resolver | 12/15 (80.00%) | 93.33% |
| Final ResolveOps | 14/15 (93.33%) | 100% |

The deterministic strict-success scorer checks this implemented benchmark contract; it is not a general semantic-entailment judgment. A strict benchmark success requires:

- an accepted diagnosis or justified abstention;
- an accepted action;
- the correct escalation decision;
- required evidence-reference coverage; and
- no forbidden structured claim-ID violation.

Verifier approval/rejection and Human Safety Gate approval are not part of this deterministic pass calculation; those behaviors are audited separately.

Required evidence-reference coverage means the required tool IDs and required source IDs appear in the candidate evidence references. The forbidden-claim component checks structured claim IDs; it does not semantically scan free-form prose. Neither check proves that every natural-language statement is semantically entailed, that every citation is perfectly attached to the correct claim, or that customer-facing prose has undergone complete semantic fact verification.

The frozen comparison carries a visible compute tradeoff: average recorded latency rose from 9,692.86 ms to 23,815.48 ms and recorded token use from 45,661 to 151,432. Investigator + Resolver had higher evidence-reference coverage and strict conjunction-level success while diagnosis, action, and escalation each remained 86.67%. The final staged configuration recorded 93.33% for those three component metrics and 100% required evidence-reference coverage.

Recorded token usage is reported, but historical dollar cost is unavailable because the run artifacts did not persist the complete pricing/accounting data needed for a defensible reconstruction. Baseline retry usage may also be undercounted where usage was unavailable.

## Hot Take

A Verifier is not independent merely because it has a different role prompt. CASE-003 is the final known benchmark failure: the Resolver conservatively abstained, and the same-model Verifier reinforced that uncertainty instead of correcting it. This observed case does not prove a universal failure mode, but it shows that role separation alone did not guarantee epistemic independence when stages shared the same model, evidence, and uncertainty assumptions. Next, we would test deliberately differentiated verification evidence or disagreement calibration.

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
| Judge Challenge | Server-side | Yes | Up to three fresh, session-only production ResolveOps runs on observable synthetic cases; never benchmark-scored. |
| Historical Replay | No | No | Direct read-only inspection of immutable official trajectories. |

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

### Expected frozen results

These are existing frozen results, not guaranteed outputs of a fresh stochastic rerun:

```text
baseline-official-004: 10/15 strict successes — 66.67%
resolveops-phase4-002: 12/15 — 80.00%
resolveops-phase5a-001: 14/15 — 93.33%

required evidence-reference coverage:
73.33% -> 93.33% -> 100.00%
```

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

The Streamlit historical playback is **OFFLINE / ZERO API COST**. In **Judge Demo**, select a recorded resolution whose action requires approval; the Safety Gate shows that simulated gateway activation is blocked pending an explicit human decision. The Human Safety Gate uses an isolated, session-local synthetic sandbox: approval changes only that sandbox's gateway/account provisioning state, while rejection leaves it unchanged. No external system, candidate, trajectory, benchmark artifact, or score is affected. Human execution remains outside deterministic benchmark scoring.

## Public output contract and safety

The public, case-agnostic root-cause and action ontology lives in `resolveops/domain/support_ontology.py`. It standardizes output labels without revealing case-specific answers. Hidden truth, accepted evaluator sets, and forbidden evaluator claims remain outside agent runtime and normal demo presentation.

Consequential simulation is deliberately separate from resolution quality: approval metadata does not alter `CandidateOutput` or VRSR scoring. ResolveOps does not claim 93% accuracy across general technical support. It demonstrates **14/15 strict benchmark successes (93.33%)** on a frozen benchmark of 15 synthetic cases spanning repeated scenario families in a controlled world with a closed public ontology; CASE-003 is the final known failure.

See [PROJECT_SPEC.md](PROJECT_SPEC.md), [TRAJECTORIES.md](TRAJECTORIES.md), [IMPROVEMENT_CHANGELOG.md](IMPROVEMENT_CHANGELOG.md), [FINAL_AUDIT.md](FINAL_AUDIT.md), and [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md) for the project record and submission status.
