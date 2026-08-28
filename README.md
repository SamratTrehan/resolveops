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

Phase 3 adds one general-purpose OpenAI Agents SDK baseline agent. It receives observable ticket inputs, has the six Phase 1 tools, and emits the fixed `CandidateOutput` contract. It has no access to evaluator-only truth. The final ResolveOps Investigator/Resolver/Verifier workflow is not implemented.

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

The frozen baseline prompt is `baseline-v1` in `resolveops/agents/baseline/prompt.py`. It is one general-purpose agent with the same six simulator capabilities intended for the later workflow. It produces the Phase 2 `CandidateOutput` schema and records local JSON trajectories without loading hidden truth.

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

The benchmark-default runtime lock is `gpt-5.6-terra` with reasoning effort `medium`. Supported effort values in the installed SDK are `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. Generation artifacts record the actual model and effort in `manifest.json` and `runtime.json`; trajectories record both per case. Existing run IDs are rejected rather than overwritten. The scoring command is deliberately separate because it is the only step that loads evaluator-only truth.

Each case receives at most one infrastructure retry, only for the recorded malformed structured-output `ModelBehaviorError`. A valid candidate is never retried based on its diagnosis, evidence, confidence, or evaluator outcome. In an `--all` run, an exhausted retry becomes a distinct `ExecutionFailure`: its trajectory and runtime record are retained, the runner continues with later cases, and it counts as a VRSR failure in the full 15-case denominator. It is not a model abstention (`INSUFFICIENT_EVIDENCE`) and does not fabricate a candidate. A run that attempted every requested case is completed even if it contains execution failures; `failure.json` is reserved for catastrophic/incomplete runs that cannot be scored.

## Planned run command

The placeholder Streamlit entry point can be started with:

```bash
python -m streamlit run streamlit_app.py
```

It currently shows only a Phase 0 status message; it does not run a support workflow.
