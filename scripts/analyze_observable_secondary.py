#!/usr/bin/env python3
"""Observable-execution secondary analysis (efficiency metrics).

Uses existing data from the resume/durable_state workload under
interrupted_execution fault.  The key contrast: interfaces with
observable execution primitives (resume, get_status) vs interfaces
without, under the same fault.

Hypothesis: observable execution primitives reduce unnecessary restarts
(logical_reexecutions), transport retries, and recovery latency, without
primarily affecting correctness.

Metrics:
  logical_reexecutions    — lower is better (fewer unnecessary restarts)
  transport_retries       — lower is better
  recovery_ms             — lower is better
  tool_calls              — lower is better

Output:
  artifacts/evidence_v02/SECONDARY_OBSERVABLE.json
  artifacts/evidence_v02/SECONDARY_OBSERVABLE.md
"""

from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
EVIDENCE = ROOT / "artifacts" / "evidence_v02"


def load(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def main() -> None:
    # ---- Resume / durable-state workload (interrupted_execution) ----
    rows = load(EVIDENCE / "resume" / "results.csv")
    by = defaultdict(list)
    for r in rows:
        by[r["interface_condition"]].append(r)

    def eff(rs: list[dict]) -> dict:
        n = len(rs)
        tc = [int(r["tool_calls"]) for r in rs]
        lr = [int(r["logical_reexecutions"]) for r in rs]
        tr = [int(r["transport_retries"]) for r in rs]
        rm = [int(r["recovery_ms"]) for r in rs if r["recovery_ms"]]
        rs2 = [1.0 if r["recovery_success"] in ("true", "True", "1") else 0.0 for r in rs]
        return {
            "runs": n,
            "tool_calls_mean": round(statistics.mean(tc), 2),
            "logical_reexecutions_mean": round(statistics.mean(lr), 2),
            "transport_retries_mean": round(statistics.mean(tr), 2),
            "recovery_success_rate": f"{int(sum(rs2))}/{n}",
            "recovery_ms_mean": round(statistics.mean(rm), 1) if rm else None,
        }

    per_interface = {i: eff(rs) for i, rs in sorted(by.items())}

    # Paired contrast: I3 (observable = resume) vs I5-minus-resumable-invocation
    def recovery_contrast(treatment: str, control: str) -> dict:
        t = {(r["task_id"], r["seed"]): r for r in by[treatment]}
        c = {(r["task_id"], r["seed"]): r for r in by[control]}
        ks = sorted(set(t) & set(c))
        t_rs = [1.0 if t[k]["recovery_success"] in ("true", "True", "1") else 0.0 for k in ks]
        c_rs = [1.0 if c[k]["recovery_success"] in ("true", "True", "1") else 0.0 for k in ks]
        t_lr = [int(t[k]["logical_reexecutions"]) for k in ks]
        c_lr = [int(c[k]["logical_reexecutions"]) for k in ks]
        return {
            "valid_pairs": len(ks),
            "recovery_success": {
                "treatment": f"{int(sum(t_rs))}/{len(t_rs)}" if t_rs else "N/A",
                "control": f"{int(sum(c_rs))}/{len(c_rs)}" if c_rs else "N/A",
            },
            "logical_reexecutions": {
                "treatment_mean": round(statistics.mean(t_lr), 2) if t_lr else None,
                "control_mean": round(statistics.mean(c_lr), 2) if c_lr else None,
            },
        }

    contrasts = {
        "I3_vs_minus_resumable": recovery_contrast("I3", "I5-minus-resumable-invocation"),
        "I5_vs_minus_resumable": recovery_contrast("I5", "I5-minus-resumable-invocation"),
        "I5_vs_minus_durable": recovery_contrast("I5", "I5-minus-durable-state"),
    }

    # ---- Postcommit-loss workload (observability under dropped response) ----
    post = load(EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv")
    post_by = defaultdict(list)
    for r in post:
        post_by[r["interface_condition"]].append(r)

    # Notable: I5 (full AFT) has reconciliation + transport handling
    # I0/I1 have no observability → extra retries
    def post_eff(rs: list[dict]) -> dict:
        n = len(rs)
        tc = [int(r["tool_calls"]) for r in rs]
        tr = [int(r["transport_retries"]) for r in rs]
        du = [1.0 if r["duplicate_effect"] in ("true", "True", "1") else 0.0 for r in rs]
        re = [1.0 if r["unknown_outcome_reconciled"] in ("true", "True", "1") else 0.0 for r in rs]
        return {
            "runs": n,
            "tool_calls_mean": round(statistics.mean(tc), 2),
            "transport_retries_mean": round(statistics.mean(tr), 2),
            "duplicate_effect_rate": f"{int(sum(du))}/{n}",
            "reconciliation_rate": f"{int(sum(re))}/{n}",
        }

    post_per_interface = {i: post_eff(rs) for i, rs in sorted(post_by.items())}

    out = {
        "status": "SECONDARY (not in the primary Holm family)",
        "design": (
            "Observable execution primitives (resume, get_status, reconciliation) "
            "enable the agent to query backend status rather than blindly retrying "
            "after interruption or response loss.  Measured from existing resume "
            "(interrupted_execution) and postcommit_loss (lost_response_after_effect) "
            "workloads."
        ),
        "resume_recovery_efficiency": per_interface,
        "resume_contrasts": contrasts,
        "postcommit_observability": post_per_interface,
        "interpretation": (
            "Interfaces without observable execution (I5-minus-resumable-invocation, "
            "I5-minus-durable-state) trigger 1.0 unnecessary logical reexecutions "
            "under interruption.  Interfaces with resume (I3, I5) recover without "
            "restart.  Under dropped-response faults, I5's reconciliation primitive "
            "eliminates transport retries (0.0 vs 0.8-1.0 for I0/I1)."
        ),
    }

    (EVIDENCE / "SECONDARY_OBSERVABLE.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# Secondary: Observable Execution — Efficiency Metrics",
        "",
        "**Status:** SECONDARY, not in the primary family.  No Holm adjustment.",
        "",
        out["design"],
        "",
        "## Resume / Durable-State (interrupted_execution fault)",
        "",
        "| Interface | Tool calls | Reexecutions | Retries | Recovery success | Recovery ms |",
        "|-----------|-----------:|-------------:|-------:|-----------------:|-----------:|",
    ]
    for i, d in sorted(per_interface.items()):
        lines.append(f"| {i} | {d['tool_calls_mean']} | {d['logical_reexecutions_mean']} | {d['transport_retries_mean']} | {d['recovery_success_rate']} | {d['recovery_ms_mean'] or '—'} |")
    lines += [
        "",
        "### Paired contrasts (recovery success)",
        "",
        "| Contrast | Pairs | Treatment recovery | Control recovery | Treatment reexec | Control reexec |",
        "|----------|------:|-------------------:|-----------------:|-----------------:|---------------:|",
    ]
    for name, c in sorted(contrasts.items()):
        lines.append(f"| {name} | {c['valid_pairs']} | {c['recovery_success']['treatment']} | {c['recovery_success']['control']} | {c['logical_reexecutions']['treatment_mean']} | {c['logical_reexecutions']['control_mean']} |")
    lines += [
        "",
        "## Postcommit-Loss (lost_response_after_effect fault)",
        "",
        "| Interface | Tool calls | Retries | Duplicate effect | Reconciliation |",
        "|-----------|-----------:|-------:|-----------------:|--------------:|",
    ]
    for i, d in sorted(post_per_interface.items()):
        lines.append(f"| {i} | {d['tool_calls_mean']} | {d['transport_retries_mean']} | {d['duplicate_effect_rate']} | {d['reconciliation_rate']} |")
    lines += [
        "",
        "## Interpretation",
        "",
        out["interpretation"],
    ]
    (EVIDENCE / "SECONDARY_OBSERVABLE.md").write_text("\n".join(lines))

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()