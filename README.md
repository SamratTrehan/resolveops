# ResolveOps

> **Work in progress:** Phase 3 adds a fair single-agent baseline implementation and local run artifacts. No official baseline result, specialized ResolveOps workflow, consequential action, or usable support interface exists yet.

ResolveOps is intended to help Tier-1 and Tier-2 technical-support agents investigate fragmented evidence, propose an evidence-backed resolution, independently verify it, and escalate when the evidence is insufficient. All data and consequential actions in this hackathon will be synthetic.

## Intended architecture

The planned flow is:

```text
Ticket -> Investigator -> evidence/tools -> Resolver -> Verifier
       -> human approval when required -> Resolution Packet
```

The repository keeps Python code under the `resolveops/` namespace: the future application package (`resolveops/app/`), agent definitions (`resolveops/agents/`), deterministic diagnostic tools (`resolveops/tools/`), domain models (`resolveops/domain/`), and evaluation code (`resolveops/evaluation/`). JSON world state and Markdown knowledge articles live in `data/`; trajectories, tests, and the Streamlit entry point remain at the repository root.

## Current phase

Phase 4 implements the first ResolveOps workflow: `Ticket -> Investigator -> EvidenceBundle -> Resolver -> CandidateOutput`. The Investigator has the six deterministic tools; the Resolver has no diagnostic tools and decides only from the ticket, public ontology, and structured evidence handoff. The independent Verifier is not implemented.

The Phase 4 hypothesis is that separating evidence collection from resolution improves evidence coverage and reduces unsupported conclusions without changing the model or tool surface. `baseline-official-004` is the frozen fair baseline (VRSR 66.67%, evidence coverage 73.33%); Phase 4 has not yet been benchmarked.

## Setup

Python 3.12 is required.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

macOS or Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Set `OPENAI_API_KEY`, `RESOLVEOPS_MODEL`, and `RESOLVEOPS_REASONING_EFFORT` in your shell before a live baseline run. The offline test suite, simulator demo, and benchmark inspection do not need them.

## Test

```bash
python -m pytest
```

## Simulator demo

With the virtual environment active, run:

```bash
python -m resolveops.tools.demo
```

The demo prints structured evidence for one synthetic customer without requiring an API key or network access.

## Benchmark inspection

```bash
python -m resolveops.evaluation.inspect_benchmark
```

This prints only observable benchmark inputs. `--show-truth` is an explicitly developer-only evaluator inspection option.

## Baseline agent

`baseline-v1` in `resolveops/agents/baseline/prompt.py` is preserved unchanged for historical reproducibility. New runs default to `baseline-v2`: the same one-agent baseline and ordinary troubleshooting instructions, plus the public output vocabulary below. It produces the Phase 2 `CandidateOutput` schema and records local JSON trajectories without loading hidden truth.

### Public support ontology

This public, case-agnostic contract lives in `resolveops/domain/support_ontology.py` and is shared by the baseline and future ResolveOps workflow. **Public ontology != case answer key.** It defines valid output labels; it does not reveal which label applies to any benchmark case.

| Root-cause ID | Generic description |
|---|---|
| `regional_outage` | Service interruption affecting the customer's area. |
| `pending_gateway_provisioning` | Replacement or new gateway activation/provisioning is incomplete. |
| `camera_reconnect_needed` | Camera needs reconnection or reconfiguration rather than being proven defective. |
| `dns_resolution_failure` | Connectivity exists but DNS/name resolution is unavailable. |
| `local_wifi_configuration` | Issue is local to Wi-Fi/client configuration rather than upstream service. |
| `account_standing_question` | Concern relates to an account notice without evidence of service suspension. |
| `INSUFFICIENT_EVIDENCE` | Available evidence does not support a reliable root cause. |

| Action ID | Generic description |
|---|---|
| `communicate_outage_status` | Communicate known outage status and next step. |
| `guide_gateway_activation` | Guide gateway activation or provisioning completion. |
| `guide_camera_reconnect` | Guide camera reconnection to the available network. |
| `guide_dns_recovery` | Guide standard DNS recovery and retest steps. |
| `guide_wifi_reconnect` | Guide local Wi-Fi/client reconnection recovery. |
| `review_account_notice` | Explain and direct review of an account-standing notice. |
| `escalate_for_more_evidence` | Escalate because evidence is insufficient for a reliable resolution. |

Configure a live model explicitly:

```powershell
$env:OPENAI_API_KEY = "..."
$env:RESOLVEOPS_MODEL = "gpt-5.6-terra"
$env:RESOLVEOPS_REASONING_EFFORT = "medium"
```

Run one development smoke case manually (this makes a live API call):

```bash
python -m resolveops.agents.baseline.runner --case-id CASE-001 --run-id smoke-001
```

The future official baseline run is explicit and is not run automatically:

```bash
python -m resolveops.agents.baseline.runner --all --run-id baseline-official-001 --official
python -m resolveops.evaluation.score_baseline_results --run-id baseline-official-001
```

Phase 4 commands are also explicit and make live API calls only when manually run with an API key:

```bash
python -m resolveops.agents.resolveops.runner --case-id CASE-001 --run-id phase4-smoke-001
python -m resolveops.agents.resolveops.runner --all --run-id resolveops-official-001
```

The benchmark-default runtime lock is `gpt-5.6-terra` with reasoning effort `medium`. Supported effort values in the installed SDK are `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. Generation artifacts record the actual model and effort in `manifest.json` and `runtime.json`; trajectories record both per case. Existing run IDs are rejected rather than overwritten. The scoring command is deliberately separate because it is the only step that loads evaluator-only truth.

`baseline-official-001` and `baseline-official-002` are incomplete historical runner attempts. `baseline-official-003` completed but is a diagnostic, non-comparable run because the baseline was not given the canonical output vocabulary. The next explicit official run using `baseline-v2` is the fair baseline comparison; no result is implied here.

Each case receives at most one infrastructure retry, only for the recorded malformed structured-output `ModelBehaviorError`. A valid candidate is never retried based on its diagnosis, evidence, confidence, or evaluator outcome. In an `--all` run, an exhausted retry becomes a distinct `ExecutionFailure`: its trajectory and runtime record are retained, the runner continues with later cases, and it counts as a VRSR failure in the full 15-case denominator. It is not a model abstention (`INSUFFICIENT_EVIDENCE`) and does not fabricate a candidate. A run that attempted every requested case is completed even if it contains execution failures; `failure.json` is reserved for catastrophic/incomplete runs that cannot be scored.

## Planned run command

The placeholder Streamlit entry point can be started with:

```bash
python -m streamlit run streamlit_app.py
```

It currently shows only a Phase 0 status message; it does not run a support workflow.
