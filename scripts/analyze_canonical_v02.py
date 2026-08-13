#!/usr/bin/env python3
"""Canonical evidence v0.2 contrast analysis (v1.1 statistical plan).

Computes the 7 pre-specified hypothesis contrasts defined in
docs/STATISTICAL_ANALYSIS_PLAN_V1.md from the canonical evidence in
artifacts/evidence_v02/, using task × seed matched pairs.

Inference per contrast:
  - paired sign-flip permutation test (10,000 permutations, seed 42)
  - task-clustered bootstrap 95% CI (2,000 resamples)
  - W/T/L in UTILITY terms (direction-aware), per the frozen convention
  - Holm correction across the 7 primary contrasts
  - H1b: one-sided non-inferiority test, frozen margin delta = 0.10

Outputs:
  artifacts/evidence_v02/CANONICAL_CONTRASTS.json
  artifacts/evidence_v02/CANONICAL_CONTRASTS.md
"""

from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
EVIDENCE = ROOT / "artifacts" / "evidence_v02"

SEED = 42
N_PERMS = 10_000
N_BOOT = 2_000
DELTA_RECALL = 0.10


def load(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def b(v) -> bool:
    return str(v).lower() in ("true", "1")


class PairedContrast:
    """A paired treatment/control contrast with direction-aware inference."""

    def __init__(self, name: str, direction: str, clusters: list[str],
                 treatment: list[float], control: list[float],
                 non_inferiority_delta: float | None = None):
        self.name = name
        self.direction = direction  # "higher" or "lower"
        self.clusters = clusters
        self.treatment = treatment
        self.control = control
        self.delta = non_inferiority_delta
        self.result: dict = {}
        self._run()

    def _utility_diff(self, t: float, c: float) -> float:
        raw = t - c
        return raw if self.direction == "higher" else -raw

    def _run(self) -> None:
        n = len(self.treatment)
        util = [self._utility_diff(t, c) for t, c in zip(self.treatment, self.control)]
        observed = sum(util) / n if n else 0.0
        wins = sum(1 for d in util if d > 1e-9)
        ties = sum(1 for d in util if abs(d) <= 1e-9)
        losses = n - wins - ties

        rng = random.Random(SEED)
        # Paired sign-flip permutation test
        count_extreme = 0
        for _ in range(N_PERMS):
            perm = sum(d * (1 if rng.random() < 0.5 else -1) for d in util) / n
            if abs(perm) >= abs(observed):
                count_extreme += 1
        raw_p = (count_extreme + 1) / (N_PERMS + 1)

        # Non-inferiority (H1b): H0 = treatment < control - delta (in raw
        # higher-is-better units). Use the raw (t - c) diffs.
        ni_p = None
        if self.delta is not None:
            raw_diffs = [t - c for t, c in zip(self.treatment, self.control)]
            ni_stat = (sum(raw_diffs) / n) + self.delta  # null: mean <= -delta
            ni_count = 0
            for _ in range(N_PERMS):
                perm = sum(d * (1 if rng.random() < 0.5 else -1) for d in raw_diffs) / n
                if perm >= ni_stat:
                    ni_count += 1
            ni_p = (ni_count + 1) / (N_PERMS + 1)

        # Task-clustered bootstrap 95% CI
        by_cluster: dict[str, list[float]] = defaultdict(list)
        for cl, d in zip(self.clusters, util):
            by_cluster[cl].append(d)
        cluster_ids = list(by_cluster.keys())
        means = []
        for _ in range(N_BOOT):
            chosen = [by_cluster[c] for c in (cluster_ids[i] for i in
                                              (rng.randrange(len(cluster_ids))
                                               for _ in range(len(cluster_ids))))]
            flat = [d for grp in chosen for d in grp]
            means.append(sum(flat) / len(flat) if flat else 0.0)
        means.sort()
        lo = means[int(0.025 * len(means))]
        hi = means[int(0.975 * len(means)) - 1] if int(0.975 * len(means)) else means[-1]

        self.result = {
            "name": self.name,
            "direction": self.direction,
            "valid_pairs": n,
            "n_task_clusters": len(cluster_ids),
            "treatment_mean": round(sum(self.treatment) / n, 4) if n else None,
            "control_mean": round(sum(self.control) / n, 4) if n else None,
            "utility_paired_difference": round(observed, 4),
            "win_tie_loss": f"{wins}/{ties}/{losses}",
            "task_clustered_95pct_CI": [round(lo, 4), round(hi, 4)],
            "raw_p_value": round(raw_p, 5),
            "non_inferiority_delta": self.delta,
            "non_inferiority_p": round(ni_p, 5) if ni_p is not None else None,
            "adjusted_p_value": None,  # filled by Holm
        }


def holm(contrasts: list[PairedContrast]) -> None:
    ordered = sorted(contrasts, key=lambda c: c.result["raw_p_value"])
    m = len(ordered)
    for rank, c in enumerate(ordered):
        p = c.result["raw_p_value"]
        c.result["adjusted_p_value"] = round(min(1.0, p * (m - rank)), 5)


def main() -> None:
    contrasts: dict[str, dict] = {}

    # ---- H1a / H1b: discovery (I2 vs I1) ----
    disc = load(EVIDENCE / "discovery" / "results.csv")
    by = defaultdict(list)
    for r in disc:
        by[r["interface_condition"]].append(r)
    i1 = {(r["task_id"], r["seed"]): r for r in by["I1"]}
    i2 = {(r["task_id"], r["seed"]): r for r in by["I2"]}
    keys = sorted(set(i1) & set(i2))
    clusters = [k[0] for k in keys]

    h1a = PairedContrast("H1a_context_exposure", "lower", clusters,
                         [float(i2[k]["context_tokens"]) for k in keys],
                         [float(i1[k]["context_tokens"]) for k in keys])
    h1b = PairedContrast("H1b_recall_non_inferiority", "higher", clusters,
                         [1.0 if b(i2[k]["state_correct_completion"]) else 0.0 for k in keys],
                         [1.0 if b(i1[k]["state_correct_completion"]) else 0.0 for k in keys],
                         non_inferiority_delta=DELTA_RECALL)

    # ---- H2 / H3: recovery ----
    res = load(EVIDENCE / "resume" / "results.csv")
    by = defaultdict(list)
    for r in res:
        by[r["interface_condition"]].append(r)
    i5 = {(r["task_id"], r["seed"]): r for r in by["I5"]}

    def recovery_contrast(name: str, ctrl: str) -> PairedContrast:
        c = {(r["task_id"], r["seed"]): r for r in by[ctrl]}
        ks = sorted(set(i5) & set(c))
        return PairedContrast(name, "higher", [k[0] for k in ks],
                              [1.0 if b(i5[k]["recovery_success"]) else 0.0 for k in ks],
                              [1.0 if b(c[k]["recovery_success"]) else 0.0 for k in ks])

    h2 = recovery_contrast("H2_resume_recovery", "I5-minus-resumable-invocation")
    h3 = recovery_contrast("H3_durable_state_recovery", "I5-minus-durable-state")

    # ---- H4a: duplicates (I4 vs I0) ----
    post = load(EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv")
    by = defaultdict(list)
    for r in post:
        by[r["interface_condition"]].append(r)
    i4 = {(r["task_id"], r["seed"]): r for r in by["I4"]}
    i0 = {(r["task_id"], r["seed"]): r for r in by["I0"]}
    ks = sorted(set(i4) & set(i0))
    h4a = PairedContrast("H4a_duplicate_effects", "lower", [k[0] for k in ks],
                         [1.0 if b(i4[k]["duplicate_effect"]) else 0.0 for k in ks],
                         [1.0 if b(i0[k]["duplicate_effect"]) else 0.0 for k in ks])

    # ---- H4b: unsafe commits (I5 vs I1, stale_state) ----
    sp = load(EVIDENCE / "effect_contract" / "stale_permission" / "results.csv")
    by = defaultdict(list)
    for r in sp:
        if r["fault_type"] == "stale_state":
            by[r["interface_condition"]].append(r)
    i1s = {(r["task_id"], r["seed"]): r for r in by["I1"]}
    i5s = {(r["task_id"], r["seed"]): r for r in by["I5"]}
    ks = sorted(set(i1s) & set(i5s))
    h4b = PairedContrast("H4b_unsafe_commits", "lower", [k[0] for k in ks],
                         [1.0 if i5s[k]["terminal_oracle_outcome"] == "unsafe_committed" else 0.0 for k in ks],
                         [1.0 if i1s[k]["terminal_oracle_outcome"] == "unsafe_committed" else 0.0 for k in ks])

    # ---- H5: incorrect terminal claims (I5 vs I5-minus-verification) ----
    ver = load(EVIDENCE / "verification" / "results.csv")
    by = defaultdict(list)
    for r in ver:
        by[r["interface_condition"]].append(r)

    def incorrect(r) -> float:
        truth = b(r["postcondition_satisfied"]) and b(r["safety_predicate_satisfied"])
        claim_success = r["terminal_agent_claim"] == "success"
        return 1.0 if claim_success != truth else 0.0

    i5v = {(r["task_id"], r["fault_type"], r["seed"]): r for r in by["I5"]}
    mv = {(r["task_id"], r["fault_type"], r["seed"]): r for r in by["I5-minus-verification"]}
    ks = sorted(set(i5v) & set(mv))
    h5 = PairedContrast("H5_incorrect_terminal_claims", "lower",
                        [k[0] for k in ks],
                        [incorrect(i5v[k]) for k in ks],
                        [incorrect(mv[k]) for k in ks])

    primary = [h1a, h1b, h2, h3, h4a, h4b, h5]
    holm(primary)

    for c in primary:
        contrasts[c.name] = c.result

    # ---- Meta tables ----
    def meta_tables() -> dict:
        disc_by = defaultdict(lambda: {"tok": [], "n": 0, "correct": 0})
        for r in load(EVIDENCE / "discovery" / "results.csv"):
            a = disc_by[r["interface_condition"]]
            a["tok"].append(float(r["context_tokens"] or 0)); a["n"] += 1
            a["correct"] += b(r["state_correct_completion"])
        res_by = defaultdict(lambda: {"rec": 0, "n": 0, "out": defaultdict(int)})
        for r in load(EVIDENCE / "resume" / "results.csv"):
            a = res_by[r["interface_condition"]]
            a["rec"] += b(r["recovery_success"]); a["n"] += 1
            a["out"][r["terminal_oracle_outcome"]] += 1
        post_by = defaultdict(lambda: {"dup": 0, "recon": 0, "n": 0})
        for r in load(EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv"):
            a = post_by[r["interface_condition"]]
            a["dup"] += b(r["duplicate_effect"]); a["recon"] += b(r["unknown_outcome_reconciled"]); a["n"] += 1
        sp_by = defaultdict(lambda: {"unsafe": 0, "abort": 0, "n": 0})
        for r in load(EVIDENCE / "effect_contract" / "stale_permission" / "results.csv"):
            if r["fault_type"] == "stale_state":
                a = sp_by[r["interface_condition"]]
                a["unsafe"] += r["terminal_oracle_outcome"] == "unsafe_committed"
                a["abort"] += r["terminal_oracle_outcome"] == "safely_aborted"
                a["n"] += 1
        ver_by = defaultdict(lambda: {"inc": 0, "n": 0})
        for r in load(EVIDENCE / "verification" / "results.csv"):
            a = ver_by[r["interface_condition"]]
            a["inc"] += incorrect(r); a["n"] += 1
        sq_by = defaultdict(lambda: {"dup": 0, "unsafe": 0, "correct": 0, "n": 0})
        for r in load(EVIDENCE / "sqlite" / "production_like" / "results.csv"):
            a = sq_by[r["interface_condition"]]
            a["dup"] += b(r["duplicate_effect"])
            a["unsafe"] += r["terminal_oracle_outcome"] == "unsafe_committed"
            a["correct"] += b(r["state_correct_completion"]); a["n"] += 1
        return {
            "discovery_tokens": {i: round(sum(a["tok"]) / a["n"], 1) for i, a in sorted(disc_by.items())},
            "discovery_correct": {i: f"{a['correct']}/{a['n']}" for i, a in sorted(disc_by.items())},
            "resume_recovery": {i: f"{a['rec']}/{a['n']}" for i, a in sorted(res_by.items())},
            "resume_outcomes": {i: dict(a["out"]) for i, a in sorted(res_by.items())},
            "postcommit_duplicates": {i: f"{a['dup']}/{a['n']}" for i, a in sorted(post_by.items())},
            "postcommit_reconciliation": {i: f"{a['recon']}/{a['n']}" for i, a in sorted(post_by.items())},
            "stale_unsafe_commits": {i: f"{a['unsafe']}/{a['n']}" for i, a in sorted(sp_by.items())},
            "stale_safely_aborted": {i: f"{a['abort']}/{a['n']}" for i, a in sorted(sp_by.items())},
            "verification_incorrect_claims": {i: f"{a['inc']}/{a['n']}" for i, a in sorted(ver_by.items())},
            "sqlite_duplicates": {i: f"{a['dup']}/{a['n']}" for i, a in sorted(sq_by.items())},
            "sqlite_unsafe": {i: f"{a['unsafe']}/{a['n']}" for i, a in sorted(sq_by.items())},
            "sqlite_correct": {i: f"{a['correct']}/{a['n']}" for i, a in sorted(sq_by.items())},
        }

    out = {"primary_contrasts": contrasts, "meta": meta_tables()}

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    with open(EVIDENCE / "CANONICAL_CONTRASTS.json", "w") as f:
        json.dump(out, f, indent=2)

    # Markdown
    lines = [
        "# AFTBench Canonical Evidence v0.2 — Pre-specified Contrasts (SAP v1.1)",
        "",
        "W/T/L counts utility (direction-aware).  p-values from paired sign-flip",
        f"permutation ({N_PERMS} perms, seed {SEED}); CIs are task-clustered bootstrap",
        f"({N_BOOT} resamples); primary family corrected with Holm (m = {len(primary)}).",
        f"H1b uses the frozen non-inferiority margin delta = {DELTA_RECALL}.",
        "",
        "| Contrast | Direction | Pairs | T mean | C mean | Util diff | W/T/L | CI95 | raw p | Holm p |",
        "|----------|-----------|------:|-------:|-------:|----------:|-------|------|------:|-------:|",
    ]
    for c in primary:
        r = c.result
        ci = f"[{r['task_clustered_95pct_CI'][0]}, {r['task_clustered_95pct_CI'][1]}]"
        lines.append(
            f"| {r['name']} | {r['direction']} | {r['valid_pairs']} | "
            f"{r['treatment_mean']} | {r['control_mean']} | {r['utility_paired_difference']} | "
            f"{r['win_tie_loss']} | {ci} | {r['raw_p_value']} | {r['adjusted_p_value']} |"
        )
    h1b_r = h1b.result
    lines += [
        "",
        f"H1b non-inferiority p (H0: recall loss >= {DELTA_RECALL}): "
        f"**{h1b_r['non_inferiority_p']}**",
        "",
        "## Meta",
        "",
        "```json",
        json.dumps(meta_tables(), indent=2),
        "```",
    ]
    with open(EVIDENCE / "CANONICAL_CONTRASTS.md", "w") as f:
        f.write("\n".join(lines))

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
