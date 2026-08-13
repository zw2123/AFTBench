#!/usr/bin/env python3
"""H5-C robustness: verification under partial success (lying response channel).

Robustness variant of H5 (NOT part of the 7-contrast primary family, NOT
Holm-adjusted with it).  The backend applies only part of the requested
effect (list-valued sub-effects truncated to their first half) while the
response channel reports full success.

Contrast: I5 vs I5-minus-verification on the partial_success workload,
task x seed matched pairs.

Endpoints:
  incorrect_terminal_claim  (claim XOR world truth)         lower is better
  partial_effect_detected   (postconditions unmet although the channel
                             claimed success, detected by verification)
  claim_corrected           (CLAIM_CORRECTED trace events)

Outputs:
  artifacts/evidence_v02/verification_partial/H5C_ROBUSTNESS.json
  artifacts/evidence_v02/verification_partial/H5C_ROBUSTNESS.md
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from analyze_canonical_v02 import PairedContrast, load, b  # noqa: E402

ROOT = Path(__file__).parent.parent
EVIDENCE = ROOT / "artifacts" / "evidence_v02"
OUT_DIR = EVIDENCE / "verification_partial"


def incorrect(r: dict) -> float:
    truth = b(r["postcondition_satisfied"]) and b(r["safety_predicate_satisfied"])
    claim_success = r["terminal_agent_claim"] == "success"
    return 1.0 if claim_success != truth else 0.0


def main() -> None:
    rows = load(OUT_DIR / "results.csv")
    by = defaultdict(list)
    for r in rows:
        by[r["interface_condition"]].append(r)

    i5 = {(r["task_id"], r["seed"]): r for r in by["I5"]}
    mv = {(r["task_id"], r["seed"]): r for r in by["I5-minus-verification"]}
    keys = sorted(set(i5) & set(mv))

    c = PairedContrast(
        "H5C_partial_success_incorrect_claims", "lower",
        [k[0] for k in keys],
        [incorrect(i5[k]) for k in keys],
        [incorrect(mv[k]) for k in keys],
    )

    # Descriptive endpoints per interface.
    def desc(rs: list[dict]) -> dict:
        n = len(rs)
        return {
            "runs": n,
            "incorrect_terminal_claims": f"{int(sum(incorrect(r) for r in rs))}/{n}",
            "false_success_rate": round(sum(incorrect(r) for r in rs) / n, 3) if n else None,
            "postconditions_unmet": f"{int(sum(1 for r in rs if not b(r['postcondition_satisfied'])))}/{n}",
        }

    # CLAIM_CORRECTED trace events per interface.
    traces = [json.loads(line) for line in open(OUT_DIR / "traces.jsonl")]
    corrected = defaultdict(int)
    for ev in traces:
        if ev.get("event_type") == "CLAIM_CORRECTED":
            corrected[ev.get("interface_condition", "?")] += 1

    out = {
        "status": "ROBUSTNESS (secondary, not in primary family)",
        "design": "partial_success lying response channel; backend applies part of the effect",
        "tasks": sorted({k[0] for k in keys}),
        "contrast": c.result,
        "per_interface": {i: desc(rs) for i, rs in sorted(by.items())},
        "claim_corrected_events": dict(sorted(corrected.items())),
        "robustness_note": (
            "H5 primary covered false_success/false_failure; H5-C extends to "
            "partial_success. Both share the same mechanism: verification "
            "reconciles the agent's terminal belief with world truth."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "H5C_ROBUSTNESS.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# H5-C Robustness — Verification Under Partial Success (SAP v1.1, secondary)",
        "",
        "Status: **robustness variant**, NOT part of the 7 primary contrasts and",
        "not Holm-adjusted with the primary family.",
        "",
        f"Design: `partial_success` lying response channel — the backend applies",
        f"only part of the effect (list-valued sub-effects truncated to their",
        f"first half) while the channel reports full success.",
        "",
        f"Tasks: {', '.join(out['tasks'])}  |  Interfaces: I4 / I5 / I5-minus-verification",
        "",
        "## Contrast: I5 vs I5-minus-verification (task x seed matched pairs)",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| valid pairs | {c.result['valid_pairs']} |",
        f"| treatment mean (I5) | {c.result['treatment_mean']} |",
        f"| control mean (I5-minus-verification) | {c.result['control_mean']} |",
        f"| utility paired difference | {c.result['utility_paired_difference']} |",
        f"| win/tie/loss | {c.result['win_tie_loss']} |",
        f"| 95% CI (task-clustered) | {c.result['task_clustered_95pct_CI']} |",
        f"| permutation p | {c.result['raw_p_value']} |",
        "",
        "## Per-interface incorrect terminal claims",
        "",
        "| Interface | Incorrect claims | False-success rate | Postconditions unmet |",
        "|-----------|------------------|--------------------|----------------------|",
    ]
    for i, d in sorted(out["per_interface"].items()):
        lines.append(f"| {i} | {d['incorrect_terminal_claims']} | {d['false_success_rate']} | {d['postconditions_unmet']} |")
    lines += [
        "",
        "## CLAIM_CORRECTED trace events",
        "",
        "```",
        json.dumps(out["claim_corrected_events"], indent=2),
        "```",
        "",
        out["robustness_note"],
    ]
    (OUT_DIR / "H5C_ROBUSTNESS.md").write_text("\n".join(lines))

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
