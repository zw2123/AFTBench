#!/usr/bin/env python3
"""Generate the 5 main paper figures from the v0.2 evidence freeze.

Figure 1: AFT model (Callability -> Operability) - conceptual diagram.
Figure 2: Primitive x Failure Mode mechanism matrix.
Figure 3: Primary effect sizes - forest plot (7 pre-specified contrasts).
Figure 4: Discovery frontier - context exposure + recall vs catalog size.
Figure 5: Synthetic vs SQLite - duplicate / unsafe-commit rates.

All data comes from artifacts/evidence_v02/ (frozen v0.2 evidence).
Outputs: paper/figures/fig1_aft_model.pdf, ... fig5_synthetic_vs_sqlite.pdf
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT = Path(__file__).parent.parent
EVIDENCE = ROOT / "artifacts" / "evidence_v02"
FIGDIR = ROOT / "paper" / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "figure.dpi": 150,
})


def load_csv(path: Path) -> list[dict]:
    with open(path) as f:
        return list(csv.DictReader(f))


def b(v) -> bool:
    return str(v).lower() in ("true", "1")


# ---------------------------------------------------------------------------
# Figure 1 - AFT model
# ---------------------------------------------------------------------------
def fig1() -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axis("off")

    # Two-stage pipeline
    stage1 = "Callability\n(static exposure of tool capability)"
    stage2 = "Operability\n(runtime execution dependability)"

    # Call-ability layer boxes
    l1 = [
        ("Representation", "typed schemas\nstructured output"),
        ("Discovery", "selective catalog\nsearch / selection"),
        ("Exposure", "context-compact\ncapability views"),
    ]
    # Oper-ability layer boxes
    l2 = [
        ("Continuity", "resume / durable\nstate"),
        ("Safety", "effect contracts\n(idempotency, versioning, preview)"),
        ("Truth", "verification / evidence\n(reconcile claims with world)"),
    ]

    # Left column
    for i, (title, sub) in enumerate(l1):
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.05, 0.72 - i * 0.28), 0.30, 0.24, boxstyle="round,pad=0.01",
            fc="#dbe9f6", ec="#2c6faa", lw=1.2))
        ax.text(0.20, 0.83 - i * 0.28, title, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(0.20, 0.745 - i * 0.28, sub, ha="center", va="center",
                fontsize=8.5, color="#333")

    # Right column
    for i, (title, sub) in enumerate(l2):
        ax.add_patch(mpatches.FancyBboxPatch(
            (0.62, 0.72 - i * 0.28), 0.30, 0.24, boxstyle="round,pad=0.01",
            fc="#e9f5e1", ec="#4a7d2c", lw=1.2))
        ax.text(0.77, 0.83 - i * 0.28, title, ha="center", va="center",
                fontsize=11, fontweight="bold")
        ax.text(0.77, 0.745 - i * 0.28, sub, ha="center", va="center",
                fontsize=8.5, color="#333")

    # Arrows
    for i in range(3):
        ax.annotate("", xy=(0.62, 0.84 - i * 0.28), xytext=(0.35, 0.84 - i * 0.28),
                    arrowprops=dict(arrowstyle="-|>", color="#555", lw=1.6))

    ax.text(0.31, 0.12, "Selective\nprimitive exposure", ha="center", fontsize=9,
            color="#555", style="italic")
    ax.text(0.485, 0.9, "Causal mechanism: interface primitives change\n"
                        "agent behavior under operational failure modes",
            ha="center", fontsize=9, color="#333")

    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig1_aft_model.pdf")
    fig.savefig(FIGDIR / "fig1_aft_model.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 2 - Primitive x Failure Mode matrix
# ---------------------------------------------------------------------------
def fig2() -> None:
    rows = [
        ("Large catalog",             [1, 0, 0, 0, 0]),
        ("Interruption",              [0, 1, 0, 0, 0]),
        ("Process-local state loss",  [0, 0, 1, 0, 0]),
        ("Stale / permission drift",  [0, 0, 0, 1, 0]),
        ("Post-commit uncertainty",   [0, 0, 0, 1, 1]),
        ("False outcome (lying channel)", [0, 0, 0, 0, 1]),
    ]
    cols = ["Discovery", "Resume", "Durable\nstate", "Effect\ncontract", "Verification"]
    M = np.array([r[1] for r in rows])

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    cmap = matplotlib.colors.ListedColormap(["#ffffff", "#2c6faa"])
    im = ax.imshow(M, cmap=cmap, aspect="auto")

    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9)

    for i in range(len(rows)):
        for j in range(len(cols)):
            if M[i, j]:
                ax.text(j, i, "\u25cf", ha="center", va="center", fontsize=14,
                        color="#1b4f7a")
    ax.set_title("Mechanism matrix: which primitive targets which failure mode")
    fig.tight_layout()
    fig.savefig(FIGDIR / "fig2_mechanism_matrix.pdf")
    fig.savefig(FIGDIR / "fig2_mechanism_matrix.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 3 - Primary effect sizes (forest plot)
# ---------------------------------------------------------------------------
def fig3() -> None:
    c = json.load(open(EVIDENCE / "CANONICAL_CONTRASTS.json"))["primary_contrasts"]
    order = ["H1a_context_exposure", "H1b_recall_non_inferiority",
             "H2_resume_recovery", "H3_durable_state_recovery",
             "H4a_duplicate_effects", "H4b_unsafe_commits",
             "H5_incorrect_terminal_claims"]

    # Panel A: H1a in kilotokens; Panel B: H1b-H5 in rate units.
    fig, (axa, axb) = plt.subplots(2, 1, figsize=(7, 7), sharex=False,
                                   gridspec_kw={"height_ratios": [1, 3]})

    # Panel A (H1a)
    d = c["H1a_context_exposure"]
    lo, hi = d["task_clustered_95pct_CI"]
    diff = d["utility_paired_difference"]
    lab = f"H1a context exposure\n(selective discovery, lower better)"
    axa.errorbar([diff / 1000.0], [1], xerr=[[(diff - lo) / 1000.0], [(hi - diff) / 1000.0]],
                 fmt="o", color="#ca3b3b", ms=8, capsize=4)
    axa.axvline(0, color="gray", lw=0.8)
    axa.set_yticks([1]); axa.set_yticklabels([lab], fontsize=9)
    axa.set_xlabel("utility effect (kilo tokens)")
    axa.set_title("(a) Discovery context exposure")

    # Panel B (H1b-H5)
    labels = []
    effs, los, his, ps = [], [], [], []
    for k in order[1:]:
        d = c[k]
        labels.append(k.replace("_", " ").title())
        effs.append(d["utility_paired_difference"])
        los.append(d["task_clustered_95pct_CI"][0])
        his.append(d["task_clustered_95pct_CI"][1])
        ps.append(d["adjusted_p_value"])
    y = np.arange(len(labels))[::-1]
    for yi, e, lo, hi, p in zip(y, effs, los, his, ps):
        m = "s" if p is not None and p < 0.05 else "D"
        col = "#2c6faa" if (p is None or p < 0.05) else "#999999"
        axb.errorbar([e], [yi], xerr=[[e - lo], [hi - e]], fmt=m,
                     color=col, ms=7, capsize=4)
        sig = "ns" if (p is not None and p >= 0.05) else f"p = {p:.4f}"
        axb.text(e + 0.03, yi, sig, va="center", fontsize=8, color="#333")
    axb.axvline(0, color="gray", lw=0.8, ls="--")
    axb.set_yticks(y); axb.set_yticklabels(labels, fontsize=8.5)
    for yi, p in zip(y, ps):
        sig = "ns" if (p is not None and p >= 0.05) else f"p = {p:.4f}"
        axb.text(effs[max(0, len(y)-1-yi)] + 0.03, yi, sig, va="center", fontsize=8, color="#333")
    axb.set_xlim(-0.1, 1.2)
    axb.set_xlabel("utility effect (rate units, W/T/L counts utility)")
    axb.set_title("(b) Recovery, safety, and verification contrasts")

    fig.suptitle("Primary pre-specified contrasts \u2014 utility effects with 95% CI",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(FIGDIR / "fig3_primary_effect_sizes.pdf")
    fig.savefig(FIGDIR / "fig3_primary_effect_sizes.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 4 - Discovery frontier
# ---------------------------------------------------------------------------
def fig4() -> None:
    rows = load_csv(EVIDENCE / "discovery" / "results.csv")
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[r["interface_condition"]][int(r["catalog_size"])].append(r)

    sizes = sorted({cs for _, d in by.items() for cs in d})
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    colors = {"I1": "#ca3b3b", "I2": "#2c6faa", "I5": "#4a7d2c"}

    for iface, color in colors.items():
        if iface not in by:
            continue
        toks = [float(np.mean([int(r["context_tokens"]) for r in by[iface][cs]]))
                for cs in sizes]
        ax1.plot(sizes, toks, "o-", color=color, label=iface)
    ax1.set_xscale("log"); ax1.set_yscale("log")
    ax1.set_xlabel("catalog size (log)"); ax1.set_ylabel("mean context tokens (log)")
    ax1.legend(); ax1.grid(alpha=0.3)
    ax1.set_title("(a) Context exposure")

    for iface, color in colors.items():
        if iface not in by:
            continue
        rec = [sum(1 for r in by[iface][cs] if b(r["state_correct_completion"])) / len(by[iface][cs])
               for cs in sizes]
        ax2.plot(sizes, [100 * v for v in rec], "o-", color=color, label=iface)
    ax2.set_xscale("log")
    ax2.set_xlabel("catalog size (log)"); ax2.set_ylabel("tool-recall (%)")
    ax2.set_ylim(0, 110); ax2.legend(); ax2.grid(alpha=0.3)
    ax2.set_title("(b) Tool recall (H1b)")

    fig.suptitle("Discovery frontier: selective discovery flattens exposure, preserves recall",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(FIGDIR / "fig4_discovery_frontier.pdf")
    fig.savefig(FIGDIR / "fig4_discovery_frontier.png")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 5 - Synthetic vs SQLite replication
# ---------------------------------------------------------------------------
def fig5() -> None:
    def rates(path, fault=None, field="duplicate_effect", value="true"):
        rows = load_csv(path)
        by = defaultdict(list)
        for r in rows:
            if fault and r["fault_type"] != fault:
                continue
            by[r["interface_condition"]].append(r)
        out = {}
        for i, rs in by.items():
            n = sum(1 for r in rs if r[field] == value)
            out[i] = 100.0 * n / len(rs)
        return out

    syn_dup = rates(EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv")
    syn_uns = rates(EVIDENCE / "effect_contract" / "stale_permission" / "results.csv",
                    fault="stale_state", field="terminal_oracle_outcome", value="unsafe_committed")
    sq_dup = rates(EVIDENCE / "sqlite" / "production_like" / "results.csv")
    sq_uns = rates(EVIDENCE / "sqlite" / "production_like" / "results.csv",
                   field="terminal_oracle_outcome", value="unsafe_committed")

    ifaces = ["I0", "I1", "I4", "I5"]
    x = np.arange(len(ifaces))
    width = 0.2
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.5, 3.6))

    for ax, metric, syn, sq, ylab in [
        (a1, "duplicate effects", syn_dup, sq_dup, "duplicate effect rate (%)"),
        (a2, "unsafe commits", syn_uns, sq_uns, "unsafe commit rate (%)"),
    ]:
        s = [syn.get(i, 0) for i in ifaces]
        q = [sq.get(i, 0) for i in ifaces]
        ax.bar(x - width / 2, s, width, label="synthetic (external_actions)", color="#ca3b3b", alpha=0.8)
        ax.bar(x + width / 2, q, width, label="SQLite (production-like)", color="#4a7d2c", alpha=0.8)
        ax.set_xticks(x); ax.set_xticklabels(ifaces)
        ax.set_ylabel(ylab)
        ax.set_title(f"({metric})")
        ax.legend(fontsize=7)

    fig.suptitle("Replication: effect contracts cut duplicates/unsafe commits in both environments",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(FIGDIR / "fig5_synthetic_vs_sqlite.pdf")
    fig.savefig(FIGDIR / "fig5_synthetic_vs_sqlite.png")
    plt.close(fig)


def main() -> None:
    fig1()
    fig2()
    fig3()
    fig4()
    fig5()
    print("Generated:")
    for p in sorted(FIGDIR.glob("fig*.pdf")):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()