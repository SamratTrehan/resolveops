# Improvement Changelog

Record measured changes without rewriting earlier results. Do not promote an iteration unless it is evaluated on the same cases and scoring definitions as the baseline.

| Stage | Hypothesis / what was tried | Why | Evidence/result | Decision | Learning |
| --- | --- | --- | --- | --- | --- |
| Baseline | _To be implemented and measured._ | Establish the simple comparison system. | _Pending._ | _Pending._ | _Pending._ |
| Iteration 1 | _Future iteration._ | _Pending._ | _Pending._ | _Pending._ | _Pending._ |
| Iteration 2 | _Future iteration._ | _Pending._ | _Pending._ | _Pending._ | _Pending._ |
| Phase 4 Investigator + Resolver | Separate evidence collection from resolution using the same Terra/medium model, tools, public ontology, and fixed cases. | Test whether organized evidence improves coverage and reduces unsupported conclusions. | Baseline starting point: `baseline-official-004`, VRSR 66.67%, evidence coverage 73.33%. Phase 4 has not been evaluated. `baseline-official-003` is excluded from fair comparison because its output vocabulary was not public. | Pending evaluation on the fixed benchmark. | Pending. |
| Phase 5A Verifier + one revision | Independently verify a resolution and permit one bounded Resolver correction. | Detect unnecessary abstention, incomplete citations, and inconsistent decisions at measurable extra cost. | Frozen Phase 4 starting point: VRSR 80.0%, evidence coverage 93.33%. Not yet evaluated. | Pending evaluation; one quality revision maximum. | Pending. |
| Phase 5B Human approval gate | Require explicit human approval before consequential synthetic execution. | Complete the safety workflow without changing resolution quality. | Frozen Phase 5A result: VRSR 93.33%; safety feature not evaluated for accuracy. | Pending safety demonstration only. | Pending. |
