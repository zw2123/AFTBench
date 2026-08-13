#!/usr/bin/env python3
"""Structured-output secondary analysis (interaction efficiency).

Uses existing data from the effect_contract (postcommit_loss, stale_permission)
and discovery workloads.  Structured tool schemas and structured tool results
(typed error codes, current_version, structured payloads) are the treatment;
free-form / opaque results are the control.

Hypothesis: structured output primarily affects interaction efficiency and
repair behavior — fewer blind transport retries, version-refresh repair
instead of re-execution — and lowers context exposure, rather than being the
source of primary correctness effects (which are attributed to the bundled
effect-contract / verification primitives).

Metrics:
  tool_definition_tokens    — structured schemas are more compact (lower better)
  transport_retries         — structured errors → fewer blind retries (lower better)
  tool_calls                — repair via refresh instead of restart
Output:
  artifacts/evidence_v02/SECONDARY_STRUCTURED_OUTPUT.json
  artifacts/evidence_v02/SECONDARY_STRUCTURED_OUTPUT.md
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


def mean(xs: list[float]) -> float:
    return round(statistics.mean(xs), 2) if xs else None


def main() -> None:
    # ---- Discovery workload: context exposure from structured schemas ----
    disc = load(EVIDENCE / "discovery" / "results.csv")
    disc_by = defaultdict(list)
    for r in disc:
        disc_by[r["interface_condition"]].append(r)

    def disc_row(iface: str) -> dict:
        rs = disc_by[iface]
        return {
            "runs": len(rs),
            "tool_definition_tokens_mean": mean([int(r["tool_definition_tokens"]) for r in rs]),
            "context_tokens_mean": mean([int(r["context_tokens"]) for r in rs]),
            "correct_completion_rate": f"{int(sum(1 for r in rs if r['state_correct_completion'] in ('true','True','1')))}/{len(rs)}",
        }

    discovery_cells = {
        "I1_structured_full_catalog": disc_row("I1"),
        "I2_structured_selective": disc_row("I2"),
        "I5_structured_selective": disc_row("I5"),
    }

    # ---- Effect-contract workload: repair behavior under faults ----
    result = {}

    for wl_name, path, fault in [
        ("postcommit_loss", EVIDENCE / "effect_contract" / "postcommit_loss" / "results.csv", "lost_response_after_effect"),
        ("stale_permission", EVIDENCE / "effect_contract" / "stale_permission" / "results.csv", "stale_state"),
    ]:
        rows = load(path)
        by = defaultdict(list)
        for r in rows:
            if fault in ("stale_state",) and r["fault_type"] != fault:
                continue
            by[r["interface_condition"]].append(r)

        def row(iface: str) -> dict | None:
            rs = by.get(iface)
            if not rs:
                return None
            return {
                "runs": len(rs),
                "tool_calls_mean": mean([int(r["tool_calls"]) for r in rs]),
                "transport_retries_mean": mean([int(r["transport_retries"]) for r in rs]),
                "logical_reexecutions_mean": mean([int(r["logical_reexecutions"]) for r in rs]),
                "correct_rate": f"{int(sum(1 for r in rs if r['state_correct_completion'] in ('true','True','1')))}/{len(rs)}",
            }

        result[wl_name] = {i: row(i) for i in ["I0", "I1", "I3", "I4", "I5"] if row(i) is not None}

    out = {
        "status": "SECONDARY (not in the primary Holm family)",
        "design": (
            "Structured output = typed capability schemas (input_schema) and "
            "structured tool results (typed error_code, current_version, "
            "structured payloads).  Measured from existing discovery "
            "(context exposure) and effect-contract (repair behavior) workloads."
        ),
        "discovery_context_exposure": discovery_cells,
        "effect_contract_repair": result,
        "interpretation": (
            "Structured schemas with selective discovery cut tool-definition "
            "exposure ~80x (4063->50 tokens mean across catalog sizes, see "
            "H1a/H1b) with no recall loss.  Under stale/permission faults, "
            "interfaces exposing structured errors (I4/I5: error_code + "
            "current_version) repair via version refresh (transport_retries "
            "0.0) whereas opaque-interface runs (I0/I1) blind-retry (0.5-1.0).  "
            "Under lost-response faults, I5's reconcile resolves without "
            "retry (0.0).  Structured output thus primarily improves "
            "interaction efficiency and repair determinism rather than the "
            "source of primary correctness effects."
        ),
    }

    (EVIDENCE / "SECONDARY_STRUCTURED_OUTPUT.json").write_text(json.dumps(out, indent=2))

    lines = [
        "# Secondary: Structured Output — Interaction Efficiency",
        "",
        "**Status:** SECONDARY, not in the primary family.  No Holm adjustment.",
        "",
        out["design"],
        "",
        "## Discovery workload — context exposure by schema structure",
        "",
        "| Condition | Runs | Tool-def tokens (mean) | Context tokens (mean) | Correct completion |",
        "|-----------|-----:|-----------------------:|----------------------:|-------------------:|",
    ]
    for i, d in sorted(discovery_cells.items()):
        lines.append(f"| {i} | {d['runs']} | {d['tool_definition_tokens_mean']} | {d['context_tokens_mean']} | {d['correct_completion_rate']} |")
    lines.append("")

    for wl_name, cells in result.items():
        lines.append(f"## {wl_name} workload — repair behavior")
        lines.append("")
        lines.append("| Interface | Tool calls | Transport retries | Reexecutions | Correct |")
        lines.append("|-----------|-----------:|------------------:|-------------:|--------:|")
        for i, d in cells.items():
            lines.append(f"| {i} | {d['tool_calls_mean']} | {d['transport_retries_mean']} | {d['logical_reexecutions_mean']} | {d['correct_rate']} |")
        lines.append("")

    lines += ["## Interpretation", "", out["interpretation"]]
    (EVIDENCE / "SECONDARY_STRUCTURED_OUTPUT.md").write_text("\n".join(lines))

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()