# Legacy Evidence — Invalidated

This directory contains pre-v0.2 benchmark evidence. All of it is
**invalidated development history**, not usable for paper claims.

## Invalidation reasons

The v0.2 debugging session (commit `a04f4fb`) found six classes of P0
measurement-validity defects that were present when this evidence was
generated:

1. **Vacuous postconditions** — task manifests carried string-format
   postconditions that no world verifier could evaluate; the checks
   returned True for nearly every run.
2. **Empty parameter propagation** — agents read `schema["properties"]`
   while I1-family interfaces wrapped schemas in `input_schema`, so every
   invocation carried default/empty parameters.
3. **Inactive fault injection** — the FaultInjector was never called by the
   runner; stale-state, permission-drift, and other faults never reached
   the backend.
4. **Cross-run interface state leakage** — interface instances were shared
   across fault/seed iterations, so I4/I5 idempotency caches produced
   phantom successes.
5. **Placeholder safety metrics** — `unintended_effect` was hard-coded
   False; `unauthorized_effect` had no logging source.
6. **Acceptance/report mismatches** — e.g., the M3 micro report claimed
   "unsafe_committed appears: PASS" while `m3_results.json` recorded that
   check as FAILED.

## Status

```yaml
evidence_status: invalidated
superseded_by: artifacts/evidence_v02/
report: reports/CANONICAL_EVIDENCE_V02.md
```

Do not delete: this history documents the benchmark's validity audit.
