#!/usr/bin/env python3
"""Canonical evidence v0.2 contrast analysis.

Computes the pre-registered hypothesis contrasts defined in
docs/STATISTICAL_ANALYSIS_PLAN_V1.md from the canonical evidence in
artifacts/evidence_v02/, using task-seed matched pairs.

Outputs:
  artifacts/evidence_v02/CANONICAL_CONTRASTS.json
  artifacts/evidence_v02/CANONICAL_CONTRASTS.md
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
EVIDENCE = ROOT / "artifacts" / "evidence_v02"


def load(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def b(v: str) -> bool:
    return str(v).lower() in ("true", "1")


def paired_mean_diff(treatment: list[float], control: list[float]) -> dict:
    pairs = [(t, c) for t, c in zip(treatment, control)]
    diffs = [t - c for t, c in pairs]
    wins = sum(1 for d in diffs if d > 1e-9)
    ties = sum(1 for d in diffs if abs(d) <= 1e-9)
    losses = sum(1 for d in diffs if d < -1e-9)
    return {
        "valid_pairs": len(pairs),
        "treatment_mean": sum(treatment) / len(treatment) if treatment else None,
        "control_mean": sum(control) / len(control) if control else None,
        "paired_difference": sum(diffs) / len(diffs) if diffs else None,
        "win_tie_loss": f"{wins}/{ties}/{losses}",
        "min": min(diffs) if diffs else None,
        "max": max(diffs) if diffs else None,
    }


def rows_by_key(rows: list[dict]) -> dict[tuple, dict]:
    out: dict[tuple, dict] = {}
    for r in rows:
        out[(r["task_id"], r["seed"])] = r
    return out


def main() -> None:
    contrasts = {}

    # ---- H1: selective discovery vs full catalog (I2 vs I1) ----
    disc = load(EVIDENCE / "discovery" / "results.csv")
    by = defaultdict(list)
    for r in disc:
        by[r["interface_condition"]].append(r)
    i1 = rows_by_key(by["I1"])
    i2 = rows_by_key(by["I2"])
    keys = sorted(set(i1) & set(i2))
    contrasts["H1_discovery_tokens"] = paired_mean_diff(
        [float(i2[k]["context_tokens"]) for k in keys],
        [float(i1[k]["context_tokens"]) for k in keys],
    )
    contrasts["H1_discovery_recall"] = paired_mean_diff(
        [1.0 if b(i2[k]["state_correct_completion"]) else 0.0 for k in keys],
        [1.0 if b(i1[k]["state_correct_completion"]) else 0.0 for k in keys],
    )
    contrasts["H1_meta"] = {
        "n_task_clusters": len({k[0] for k in keys}),
        "context_tokens_by_interface": {
            i: round(sum(float(r["context_tokens"]) for r in rs) / len(rs), 1)
            for i, rs in sorted(by.items())
        },
        "correct_by_interface": {
            i: f"{sum(1 for r in rs if b(r['state_correct_completion']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
    }

    # ---- H2/H3: resume + durable state (interruption_recovery) ----
    res = load(EVIDENCE / "resume" / "results.csv")
    by = defaultdict(list)
    for r in res:
        by[r["interface_condition"]].append(r)
    i5 = rows_by_key(by["I5"])
    for name, ctrl_name in [("H2_resume", "I5-minus-resumable-invocation"),
                            ("H3_durable_state", "I5-minus-durable-state")]:
        ctrl = rows_by_key(by[ctrl_name])
        keys = sorted(set(i5) & set(ctrl))
        contrasts[name] = paired_mean_diff(
            [1.0 if b(i5[k]["recovery_success"]) else 0.0 for k in keys],
            [1.0 if b(ctrl[k]["recovery_success"]) else 0.0 for k in keys],
        )
    contrasts["H2_H3_meta"] = {
        "n_task_clusters": len({k[0] for k in keys}),
        "recovery_by_interface": {
            i: f"{sum(1 for r in rs if b(r['recovery_success']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
        "outcome_by_interface": {
            i: {o: sum(1 for r in rs if r["terminal_oracle_outcome"] == o)
                for o in sorted({r["terminal_oracle_outcome"] for r in rs})}
            for i, rs in sorted(by.items())
        },
    }

    # ---- H4: duplicate effects (postcommit_loss) ----
    post = load(EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv")
    by = defaultdict(list)
    for r in post:
        by[r["interface_condition"]].append(r)
    i4 = rows_by_key(by["I4"])
    legacy = rows_by_key(by["I0"])
    keys = sorted(set(i4) & set(legacy))
    contrasts["H4_duplicate_I4_vs_I0"] = paired_mean_diff(
        [1.0 if b(i4[k]["duplicate_effect"]) else 0.0 for k in keys],
        [1.0 if b(legacy[k]["duplicate_effect"]) else 0.0 for k in keys],
    )
    contrasts["H4_meta"] = {
        "n_task_clusters": len({k[0] for k in keys}),
        "duplicates_by_interface": {
            i: f"{sum(1 for r in rs if b(r['duplicate_effect']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
        "reconciliation_by_interface": {
            i: f"{sum(1 for r in rs if b(r['unknown_outcome_reconciled']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
    }

    # ---- H4b: unsafe commits (stale_permission) ----
    sp = load(EVIDENCE / "effect_contract" / "stale_permission" / "results.csv")
    by = defaultdict(list)
    for r in sp:
        if r["fault_type"] == "stale_state":
            by[r["interface_condition"]].append(r)
    i1 = rows_by_key(by["I1"])
    i5 = rows_by_key(by["I5"])
    keys = sorted(set(i1) & set(i5))
    contrasts["H4_unsafe_I5_vs_I1"] = paired_mean_diff(
        [1.0 if b(i5[k]["state_correct_completion"]) else 0.0 for k in keys],
        [1.0 if b(i1[k]["state_correct_completion"]) else 0.0 for k in keys],
    )
    contrasts["H4_unsafe_commits_I1_vs_I5"] = paired_mean_diff(
        [1.0 if i1[k]["terminal_oracle_outcome"] == "unsafe_committed" else 0.0 for k in keys],
        [1.0 if i5[k]["terminal_oracle_outcome"] == "unsafe_committed" else 0.0 for k in keys],
    )
    contrasts["H4b_meta"] = {
        "n_task_clusters": len({k[0] for k in keys}),
        "unsafe_committed_by_interface": {
            i: f"{sum(1 for r in rs if r['terminal_oracle_outcome'] == 'unsafe_committed')}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
        "safely_aborted_by_interface": {
            i: f"{sum(1 for r in rs if r['terminal_oracle_outcome'] == 'safely_aborted')}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
    }

    # ---- H5: verification (postcommit I5 vs I5-minus-verification) ----
    by5 = defaultdict(list)
    for r in post:
        by5[r["interface_condition"]].append(r)
    i5p = rows_by_key(by5["I5"])
    mvp = rows_by_key(by5["I5-minus-verification"])
    keys = sorted(set(i5p) & set(mvp))
    contrasts["H5_verification"] = paired_mean_diff(
        [1.0 if b(i5p[k]["state_correct_completion"]) else 0.0 for k in keys],
        [1.0 if b(mvp[k]["state_correct_completion"]) else 0.0 for k in keys],
    )
    contrasts["H5_meta"] = {
        "n_task_clusters": len({k[0] for k in keys}),
        "correct_by_interface": {
            i: f"{sum(1 for r in rs if b(r['state_correct_completion']))}/{len(rs)}"
            for i, rs in sorted(by5.items())
        },
    }

    # ---- SQLite external validity ----
    sq = load(EVIDENCE / "sqlite" / "production_like" / "results.csv")
    by = defaultdict(list)
    for r in sq:
        by[r["interface_condition"]].append(r)
    contrasts["SQLITE_meta"] = {
        "n_runs": len(sq),
        "duplicates_by_interface": {
            i: f"{sum(1 for r in rs if b(r['duplicate_effect']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
        "unsafe_committed_by_interface": {
            i: f"{sum(1 for r in rs if r['terminal_oracle_outcome'] == 'unsafe_committed')}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
        "correct_by_interface": {
            i: f"{sum(1 for r in rs if b(r['state_correct_completion']))}/{len(rs)}"
            for i, rs in sorted(by.items())
        },
    }

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with open(EVIDENCE / "CANONICAL_CONTRASTS.json", "w") as f:
        json.dump(contrasts, f, indent=2)

    # Markdown report
    lines = [
        "# AFTBench Canonical Evidence v0.2 — Pre-registered Contrasts",
        "",
        "Contrasts follow the frozen statistical analysis plan",
        "(`docs/STATISTICAL_ANALYSIS_PLAN_V1.md`).  All contrasts use",
        "task × seed matched pairs from `artifacts/evidence_v02/`.",
        "",
        "## Summary",
        "",
        "| Contrast | Valid pairs | Treatment | Control | Paired diff | W/T/L |",
        "|----------|------------:|----------:|--------:|------------:|-------|",
    ]
    for name, meta in [
        ("H1 context exposure (I2 vs I1)", "H1_discovery_tokens"),
        ("H1 recall (I2 vs I1)", "H1_discovery_recall"),
        ("H2 recovery (I5 vs I5-minus-resume)", "H2_resume"),
        ("H3 recovery (I5 vs I5-minus-durable)", "H3_durable_state"),
        ("H4 duplicates (I4 vs I0)", "H4_duplicate_I4_vs_I0"),
        ("H4b unsafe commits (I5 vs I1)", "H4_unsafe_I5_vs_I1"),
        ("H5 correctness (I5 vs I5-minus-verification)", "H5_verification"),
    ]:
        c = contrasts[meta]
        fmt = lambda v: "—" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))
        lines.append(
            f"| {name} | {c['valid_pairs']} | {fmt(c['treatment_mean'])} | "
            f"{fmt(c['control_mean'])} | {fmt(c['paired_difference'])} | "
            f"{c['win_tie_loss'].replace('/', '/')} |"
        )
    lines += [
        "",
        "## Details",
        "",
        "```json",
        json.dumps(contrasts, indent=2),
        "```",
    ]
    with open(EVIDENCE / "CANONICAL_CONTRASTS.md", "w") as f:
        f.write("\n".join(lines))

    print(json.dumps(contrasts, indent=2))


if __name__ == "__main__":
    main()
