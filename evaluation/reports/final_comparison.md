# ResolveOps final comparison

| Run | Architecture | VRSR | Evidence | Latency ms | Tokens |
|---|---|---:|---:|---:|---:|
| baseline-official-004 | Baseline v2 | 66.67% | 73.33% | 9692.86 | 45661 |
| resolveops-phase4-002 | Investigator -> Resolver | 80.00% | 93.33% | 17451.30 | 112636 |
| resolveops-phase5a-001 | Investigator -> Resolver -> Verifier -> optional revision | 93.33% | 100.00% | 23815.48 | 151432 |

VRSR: 66.67% -> 80.00% -> 93.33%; evidence coverage: 73.33% -> 93.33% -> 100.00%. Higher reliability came with latency/token cost.
