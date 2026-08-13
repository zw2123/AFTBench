# AFTBench Canonical Evidence v0.2 — Pre-specified Contrasts (SAP v1.1)

W/T/L counts utility (direction-aware).  p-values from paired sign-flip
permutation (10000 perms, seed 42); CIs are task-clustered bootstrap
(2000 resamples); primary family corrected with Holm (m = 7).
H1b uses the frozen non-inferiority margin delta = 0.1.

| Contrast | Direction | Pairs | T mean | C mean | Util diff | W/T/L | CI95 | raw p | Holm p |
|----------|-----------|------:|-------:|-------:|----------:|-------|------|------:|-------:|
| H1a_context_exposure | lower | 24 | 49.5833 | 4062.75 | 4013.1667 | 24/0/0 | [705.25, 8395.3333] | 0.0001 | 0.0007 |
| H1b_recall_non_inferiority | higher | 24 | 1.0 | 0.9167 | 0.0833 | 2/22/0 | [0.0, 0.1667] | 0.49875 | 0.49875 |
| H2_resume_recovery | higher | 24 | 1.0 | 0.0 | 1.0 | 24/0/0 | [1.0, 1.0] | 0.0001 | 0.0006 |
| H3_durable_state_recovery | higher | 24 | 1.0 | 0.0 | 1.0 | 24/0/0 | [1.0, 1.0] | 0.0001 | 0.0005 |
| H4a_duplicate_effects | lower | 24 | 0.0 | 0.75 | 0.75 | 18/6/0 | [0.375, 1.0] | 0.0001 | 0.0004 |
| H4b_unsafe_commits | lower | 24 | 0.0 | 0.625 | 0.625 | 15/9/0 | [0.25, 0.875] | 0.0003 | 0.0006 |
| H5_incorrect_terminal_claims | lower | 48 | 0.0 | 1.0 | 1.0 | 48/0/0 | [1.0, 1.0] | 0.0001 | 0.0003 |

H1b non-inferiority p (H0: recall loss >= 0.1): **0.0001**

## Meta

```json
{
  "discovery_tokens": {
    "I1": 4062.8,
    "I2": 49.6,
    "I5": 49.6,
    "I5-minus-selective-discovery": 4060.8
  },
  "discovery_correct": {
    "I1": "22/24",
    "I2": "24/24",
    "I5": "24/24",
    "I5-minus-selective-discovery": "22/24"
  },
  "resume_recovery": {
    "I2": "0/24",
    "I3": "24/24",
    "I5": "24/24",
    "I5-minus-durable-state": "0/24",
    "I5-minus-resumable-invocation": "0/24"
  },
  "resume_outcomes": {
    "I2": {
      "completed_as_requested": 24
    },
    "I3": {
      "completed_as_requested": 24
    },
    "I5": {
      "completed_as_requested": 24
    },
    "I5-minus-durable-state": {
      "failure": 24
    },
    "I5-minus-resumable-invocation": {
      "failure": 24
    }
  },
  "postcommit_duplicates": {
    "I0": "18/24",
    "I1": "24/24",
    "I3": "24/24",
    "I4": "0/24",
    "I5": "0/24",
    "I5-minus-side-effect-contract": "0/24",
    "I5-minus-verification": "0/24"
  },
  "postcommit_reconciliation": {
    "I0": "0/24",
    "I1": "0/24",
    "I3": "0/24",
    "I4": "0/24",
    "I5": "24/24",
    "I5-minus-side-effect-contract": "24/24",
    "I5-minus-verification": "24/24"
  },
  "stale_unsafe_commits": {
    "I1": "15/24",
    "I3": "18/24",
    "I4": "0/24",
    "I5": "0/24",
    "I5-minus-side-effect-contract": "18/24"
  },
  "stale_safely_aborted": {
    "I1": "0/24",
    "I3": "0/24",
    "I4": "6/24",
    "I5": "6/24",
    "I5-minus-side-effect-contract": "0/24"
  },
  "verification_incorrect_claims": {
    "I4": "48.0/48",
    "I5": "0.0/48",
    "I5-minus-verification": "48.0/48"
  },
  "sqlite_duplicates": {
    "I0": "9/36",
    "I1": "9/36",
    "I4": "0/36",
    "I5": "0/36"
  },
  "sqlite_unsafe": {
    "I0": "3/36",
    "I1": "3/36",
    "I4": "0/36",
    "I5": "0/36"
  },
  "sqlite_correct": {
    "I0": "36/36",
    "I1": "36/36",
    "I4": "36/36",
    "I5": "36/36"
  }
}
```