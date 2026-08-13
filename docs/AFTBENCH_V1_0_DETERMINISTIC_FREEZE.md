# AFTBench Deterministic v1.0 — Evidence Freeze

**Status:** FROZEN — deterministic evidence v1.0. Benchmark semantics are
locked as of this commit. No further semantic changes; only provider-adapter,
API-parsing, or infrastructure fixes are permitted hereafter.

## Pinned identifiers

| Item | Value |
|------|-------|
| Evidence freeze commit (all code + evidence) | `5351f5d` |
| Freeze documentation + tag commit | `6a4bb21` |
| Tag | `aftbench-v1.0-deterministic` (points at `6a4bb21`) |
| SAP v1.0 (preregistered, H1–H4) | commit `82ba77d` (plan decided at `d7fcf84`) |
| SAP v1.1 (pre-specified, 7-contrast family + H5) | commit `1e1f565` (co-committed with H5 evidence) |
| SAP doc sha256 (v1.1, frozen) | `d9f540af2e30440f…` (docs/STATISTICAL_ANALYSIS_PLAN_V1.md) |

### Evidence source hashes (from `source_state.json`)

| Workload | task_data_hash | config_hash | schema_hash | source_tree_hash |
|----------|---------------|-------------|-------------|------------------|
| discovery | `25a4fa74e4a558bf` | `c617c75195cba4ef` | `533dd821e2387b9a` | `d8766fe7c02630e4` |
| resume | `25a4fa74e4a558bf` | — | — | — |
| effect_contract/postcommit_loss | `25a4fa74e4a558bf` | — | — | — |
| effect_contract/stale_permission | `25a4fa74e4a558bf` | — | — | — |
| verification | `25a4fa74e4a558bf` | `e3aba19cc7b7fa31` | `b9e4cc36dfde388e` | `a3901947e7a5b7a5` |
| verification_partial (H5-C) | `c8ff4699d645aec6` | `5acd64ab2c89aff0` | `7b9553fb493a13ed` | `20746b4e393cd002` |
| sqlite/production_like | `25a4fa74e4a558bf` | `02b8777060f71685` | `533dd821e2387b9a` | `d8766fe7c02630e4` |

### Analysis scripts (sha256 prefix)

| Script | Hash |
|--------|------|
| scripts/analyze_canonical_v02.py | `1838dca26421fcbc` |
| scripts/analyze_h5c_robustness.py | `be897d80d2dc5d81` |
| scripts/analyze_observable_secondary.py | `7a0e29dd044ffe42` |
| scripts/analyze_structured_output_secondary.py | `6f14ae1e6b90f24f` |
| scripts/generate_paper_figures.py | `8733967d025ecbea` |
| scripts/check_deterministic_v1.py | `e44a5b41ee3c72b3` |

## Primary evidence (pre-specified, Holm family of 7)

| Contrast | Direction | Utility diff | 95% CI (task-clustered) | Holm adj. p |
|----------|-----------|-------------:|--------------------------|------------:|
| H1a context exposure (I2 vs I1) | lower | 4013.17 tokens | [705.25, 8395.33] | 0.0007 |
| H1b recall non-inferiority (I2 vs I1, δ=0.10) | higher | 0.0833 | [0.0, 0.1667] | NI p = 0.0001 |
| H2 resume recovery (I5 vs minus-resume) | higher | 1.00 | [1.0, 1.0] | 0.0006 |
| H3 durable-state recovery (I5 vs minus-durable) | higher | 1.00 | [1.0, 1.0] | 0.0005 |
| H4a duplicate effects (I4 vs I0) | lower | 0.75 | [0.375, 1.0] | 0.0004 |
| H4b unsafe commits (I5 vs I1) | lower | 0.625 | [0.25, 0.875] | 0.0006 |
| H5 incorrect terminal claims (I5 vs minus-verif.) | lower | 1.00 | [1.0, 1.0] | 0.0003 |

## Robustness & secondaries (NOT in the primary family)

- **H5-C partial success** (verification_partial, 27 runs): I5 corrects 9/9
  false terminal claims vs 9/9 uncorrected for I5-minus-verification;
  utility diff 1.0, permutation p = 0.0031. Robustness variant of H5.
- **Observable execution** (from resume + postcommit-loss evidence): resume
  eliminates unnecessary restarts (logical_reexecutions 1.0 → 0.0); I5
  reconciliation eliminates transport retries (0.8–1.0 → 0.0).
- **Structured output** (from discovery + effect-contract evidence): structured
  schemas + selective discovery cut exposure 4063 → 50 tokens (~80×); typed
  errors cut blind retries (0.5–1.0 → 0.0).

## Acceptance gate (run `python scripts/check_deterministic_v1.py`)

All gates PASS except the working-tree-clean gate, which is checked before
committing; after this freeze commit the tree is clean and the audit passes.

## Paper artifacts

- `paper/figures/fig1_aft_model.pdf/.png`
- `paper/figures/fig2_mechanism_matrix.pdf/.png`
- `paper/figures/fig3_primary_effect_sizes.pdf/.png`
- `paper/figures/fig4_discovery_frontier.pdf/.png`
- `paper/figures/fig5_synthetic_vs_sqlite.pdf/.png`

## Freeze discipline

From this commit onward:
- Benchmark semantics (worlds, faults, tasks, treatments, endpoints, verifiers)
  may NOT be changed to improve results.
- Allowed fixes only: provider-adapter bugs, API parsing bugs, infrastructure
  failures. Any semantic change requires a new benchmark version + full re-run.
