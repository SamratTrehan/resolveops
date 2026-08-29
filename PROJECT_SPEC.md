# ResolveOps Project Specification

## User and problem

- **Intended user:** Tier-1 and Tier-2 technical-support agents.
- **Problem:** evidence needed to diagnose a support case is fragmented across account state, device diagnostics, outages, ticket history, and knowledge articles.
- **Product promise:** ResolveOps investigates through tools, builds an evidence-backed resolution, verifies its conclusion, and escalates rather than guesses when evidence is insufficient.

## Proposed workflow

```text
Ticket -> Investigator -> evidence/tools -> Resolver -> Verifier
       -> human approval when required -> final Resolution Packet
```

Each stage has a distinct responsibility. The Investigator gathers relevant evidence through deterministic simulated tools. The Resolver proposes a diagnosis and next steps grounded in that evidence. A separate Verifier stage checks the proposal and may request one bounded correction. Any simulated state-changing action requires explicit human approval before synthetic execution.

## Baseline and evaluation

The baseline will be one general-purpose tool-using agent operating with the same underlying model, tool environment, and evaluation cases as the final system, but without specialized orchestration or independent verification.

The primary metric is **Verified Resolution Success Rate (VRSR)**, a strict deterministic conjunction implemented by the benchmark scorer. A case passes only when it has an accepted diagnosis or justified abstention, accepted action, correct escalation decision, required evidence-reference coverage, and no forbidden critical claim. Verifier approval/rejection and Human Safety Gate approval are audited separately; neither is part of this model-quality score.

Secondary metrics are:

- diagnosis accuracy;
- required evidence-reference coverage;
- correct tool use;
- action correctness;
- escalation correctness;
- unsupported claims;
- latency; and
- cost.

Baseline and final approaches will be evaluated on the same synthetic cases with the same scoring definitions. Representative trajectories and an improvement changelog will record how design changes affect results.

Project chronology fixed the benchmark during local/private development before the agent workflow implementation; public Git history is not presented as independent proof of that private chronology. Observable cases contain only ticket text and investigation identifiers; evaluator-only truth is stored separately. Systems submit normalized structured outputs containing a root cause (or `INSUFFICIENT_EVIDENCE`), action, escalation decision, evidence references, and non-primary prose. Component diagnosis, action, escalation, required evidence-reference coverage, and forbidden-claim metrics are reported separately.

Required evidence-reference coverage checks that required tool IDs and source IDs are present in the candidate references. It does not establish full semantic entailment for every sentence, perfect claim-to-citation attachment, or complete semantic fact verification of customer-facing prose.

The initial comparison system is one general-purpose tool-using baseline agent with a configurable runtime model and the same observable environment/tool surface as the future workflow. Its frozen prompt and local trajectories are recorded per run. Candidate generation is separated from evaluator-only scoring so baseline runtime code cannot load benchmark truth; no official benchmark result is recorded until an explicitly requested all-case run.

The baseline and future ResolveOps workflow share a public, case-agnostic support ontology for root-cause and action output IDs. It is not an answer key: it exposes valid normalized labels and generic meanings, never case-specific correct answers, required tools, or forbidden claims. Candidate root-cause and action fields are constrained to this vocabulary so exact deterministic scoring evaluates the public contract rather than hidden enum naming. `INSUFFICIENT_EVIDENCE` remains a valid model abstention and is distinct from an execution failure.

Phase 4 introduced an Investigator and Resolver; Phase 5A added a separate Verifier and at most one Resolver revision. All stages use the same runtime model and reasoning effort as the fair baseline. Role separation improves the measured result but does not itself guarantee epistemic independence, as the retained CASE-003 failure demonstrates.

Consequential simulated actions are separated from resolution quality by an explicit human-approval gate. Approval is required before synthetic execution of actions that could imply provisioning or device-state change; no approval is inferred from an agent output. This safety metadata does not alter CandidateOutput, scoring, or the benchmark.

Benchmark execution permits one infrastructure retry per case only for a malformed structured-output failure. A valid candidate is not retried based on any quality or evaluator signal. In all-case evaluation, a case that exhausts that retry becomes an explicit `ExecutionFailure`, retaining its trajectory and runtime information while the runner proceeds to remaining cases. It receives a failed case score and zero for diagnosis, action, escalation, and evidence metrics, so every component metric and VRSR use the full fixed-case denominator. This is distinct from a valid `INSUFFICIENT_EVIDENCE` abstention. A run that attempts all requested cases is completed even if some are execution failures; run-level incomplete metadata is reserved for catastrophic failures that prevent all requested cases from being attempted or persisted. The shared evaluation contract is intended for the future ResolveOps workflow as well as the baseline.

## Safety boundary

All customer, device, and account information is synthetic. Consequential actions are simulations and require human approval. ResolveOps will not connect to or modify real customer systems.

## Non-goals

- production integrations;
- authentication;
- real customer systems;
- autonomous real-world account or device changes;
- production deployment infrastructure; and
- agent, simulator, or evaluation implementation during Phase 0.
