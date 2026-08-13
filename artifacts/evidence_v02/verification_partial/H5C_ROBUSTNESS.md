# H5-C Robustness — Verification Under Partial Success (SAP v1.1, secondary)

Status: **robustness variant**, NOT part of the 7 primary contrasts and
not Holm-adjusted with the primary family.

Design: `partial_success` lying response channel — the backend applies
only part of the effect (list-valued sub-effects truncated to their
first half) while the channel reports full success.

Tasks: ea_01_create_meeting, ea_07_partial_multi_recipient, ea_09_partial_success_invite  |  Interfaces: I4 / I5 / I5-minus-verification

## Contrast: I5 vs I5-minus-verification (task x seed matched pairs)

| Field | Value |
|-------|-------|
| valid pairs | 9 |
| treatment mean (I5) | 0.0 |
| control mean (I5-minus-verification) | 1.0 |
| utility paired difference | 1.0 |
| win/tie/loss | 9/0/0 |
| 95% CI (task-clustered) | [1.0, 1.0] |
| permutation p | 0.0031 |

## Per-interface incorrect terminal claims

| Interface | Incorrect claims | False-success rate | Postconditions unmet |
|-----------|------------------|--------------------|----------------------|
| I4 | 9/9 | 1.0 | 9/9 |
| I5 | 0/9 | 0.0 | 9/9 |
| I5-minus-verification | 9/9 | 1.0 | 9/9 |

## CLAIM_CORRECTED trace events

```
{
  "I5": 9
}
```

H5 primary covered false_success/false_failure; H5-C extends to partial_success. Both share the same mechanism: verification reconciles the agent's terminal belief with world truth.