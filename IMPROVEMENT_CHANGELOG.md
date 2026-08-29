# Improvement Changelog

Record measured changes without rewriting earlier results. Do not promote an iteration unless it is evaluated on the same cases and scoring definitions as the baseline.

| Stage | Hypothesis / what was tried | Why | Evidence/result | Decision | Learning |
| --- | --- | --- | --- | --- | --- |
| Baseline v2 | One general-purpose tool-using agent with the public output ontology. | Establish a fair, simple comparison using the same cases, model, and tool environment. | `baseline-official-004`: 10/15, VRSR 66.67%, evidence coverage 73.33%. | Frozen fair baseline. | Public normalized labels are required for exact deterministic scoring to measure troubleshooting rather than hidden naming. |
| Iteration 1 | _Future iteration._ | _Pending._ | _Pending._ | _Pending._ | _Pending._ |
| Iteration 2 | _Future iteration._ | _Pending._ | _Pending._ | _Pending._ | _Pending._ |
| Phase 4 Investigator + Resolver | Separate evidence collection from resolution using the same Terra/medium model, tools, public ontology, and fixed cases. | Test whether organized evidence improves coverage and reduces unsupported conclusions. | `resolveops-phase4-002`: 12/15, VRSR 80.00%, evidence coverage 93.33%. `baseline-official-003` remains excluded because its output vocabulary was not public. | Retained as the measured two-stage workflow. | Structured evidence handoff improved both VRSR and evidence coverage over the fair baseline. |
| Phase 5A Verifier + one revision | Independently verify a resolution and permit one bounded Resolver correction. | Detect unnecessary abstention, incomplete citations, and inconsistent decisions at measurable extra cost. | `resolveops-phase5a-001`: 14/15, VRSR 93.33%, evidence coverage 100.00%, zero forbidden-claim violations. | Retained as the final measured workflow. | Independent verification and a bounded correction improved reliability, with higher recorded latency and token use. |
| Phase 5B Human approval gate | Require explicit human approval before consequential synthetic execution. | Complete the safety workflow without changing resolution quality. | Safety gate is demonstrated separately; CandidateOutput and benchmark scoring remain unchanged. | Retained as a safety boundary, not a quality metric. | Safety approval must stay outside agent judgment and outcome scoring. |
