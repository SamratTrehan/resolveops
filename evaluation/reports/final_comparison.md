# ResolveOps final comparison

| Run | Architecture | Strict success (VRSR) | Required evidence-reference coverage | Latency ms | Tokens |
|---|---|---:|---:|---:|---:|
| baseline-official-004 | Baseline v2 | 66.67% | 73.33% | 9692.86 | 45661 |
| resolveops-phase4-002 | Investigator -> Resolver | 80.00% | 93.33% | 17451.30 | 112636 |
| resolveops-phase5a-001 | Investigator -> Resolver -> Verifier -> optional revision | 93.33% | 100.00% | 23815.48 | 151432 |

Strict benchmark success: 66.67% -> 80.00% -> 93.33%; required evidence-reference coverage: 73.33% -> 93.33% -> 100.00%. Higher reliability came with latency/token cost.

VRSR is the strict conjunction of accepted diagnosis/abstention, accepted action, correct escalation, required evidence references, and no forbidden critical claim. Verifier decisions and human approval are audited separately.
