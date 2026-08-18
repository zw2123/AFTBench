# AFTBench — Work Log

## 2026-08-13 — Deterministic v1.0 freeze + LLM validation scaffolding

### Session summary

Deterministic evidence moved from "Category B+" to a frozen, audited
**Deterministic v1.0** (tag `aftbench-v1.0-deterministic`), followed by the
first stage of LLM ecological-validation infrastructure.

### Completed this session

| # | Item | Result |
|---|------|--------|
| 1 | SAP provenance audit | Confirmed v1.0 (`82ba77d`) genuinely preregisters H1–H4; v1.1 (`1e1f565`) is **pre-specified, not preregistered** (co-committed with H5 evidence). All docs/scripts re-labeled honestly. Commit `fc92cc5`. |
| 2 | H5-C partial-success robustness | New `partial_success` fault (backend applies part of effect, channel claims success). 27 runs: I5 corrects 9/9 vs 9/9 uncorrected for I5-minus-verification (utility diff 1.0, p=0.0031). Robustness variant, excluded from primary Holm family. |
| 3 | Observable-execution secondary | From existing resume/postcommit data: unnecessary restarts 1.0→0.0 (resume), transport retries 0.8–1.0→0.0 (reconcile). `SECONDARY_OBSERVABLE.{json,md}` |
| 4 | Structured-output secondary | Structured schemas + selective discovery: exposure 4063→50 tok (~80×); typed errors cut blind retries 0.5–1.0→0.0. `SECONDARY_STRUCTURED_OUTPUT.{json,md}` |
| 5 | Paper figures (5) | fig1 AFT model, fig2 mechanism matrix, fig3 primary forest plot, fig4 discovery frontier, fig5 synthetic-vs-SQLite — all from v0.2 evidence. `paper/figures/` |
| 6 | v1.0 acceptance audit | `scripts/check_deterministic_v1.py` — **107/107 gates PASS** (clean-tree gate passes after commit). |
| 7 | Freeze commit + tag | `5351f5d` (evidence+code), `6a4bb21`+`3ab7c32` (freeze docs), tag `aftbench-v1.0-deterministic` @ `3ab7c32`. |
| 8 | Freeze doc | `docs/AFTBENCH_V1_0_DETERMINISTIC_FREEZE.md` — pinned commit/tag/task/config/schema/SAP/script hashes + freeze discipline. |
| 9 | LLM validation scaffolding | `src/aftbench/llm/` (env loader, provider ABC, OpenAI-compatible client, registry), rewritten `optional_llm.py` on registry, `configs/llm/providers.yaml` (3 models, no secrets), `.env.example`, `configs/llm/pilot_qwen.yaml`, `docs/LLM_VALIDATION.md`. Commit `4013c90`. |

### Primary evidence (frozen, Holm family of 7)

| Contrast | Direction | Utility diff | Holm adj. p |
|----------|-----------|------------:|------------:|
| H1a context exposure (I2 vs I1) | lower | 4013.17 tok | 0.0007 |
| H1b recall non-inferiority (δ=0.10) | higher | 0.0833 | NI p=0.0001 |
| H2 resume recovery | higher | 1.00 | 0.0006 |
| H3 durable-state recovery | higher | 1.00 | 0.0005 |
| H4a duplicate effects | lower | 0.75 | 0.0004 |
| H4b unsafe commits | lower | 0.625 | 0.0006 |
| H5 incorrect terminal claims | lower | 1.00 | 0.0003 |

Robustness: H5-C partial success 1.00 (p=0.0031, secondary).
Secondaries: observable execution, structured output (descriptive, no Holm).

### State

- Tests: **439 passed** (424 pre-session + 15 new LLM framework tests).
- Audit: **107/107 gates PASS**.
- Working tree: clean.
- HEAD: `4013c90`; tag: `aftbench-v1.0-deterministic` → `3ab7c32`.

### Next steps (in priority order)

1. **LLM pilot** — user adds keys to `.env` (copy from `.env.example`), run
   `python -m aftbench run --config configs/llm/pilot_qwen.yaml` to validate
   the adapter end-to-end on the H5-mirror workload.
2. **LLM main matrix** — three models (qwen-3.7-plus, deepseek-v4-pro,
   gpt-5.6-sol) × four hypotheses (H1 Discovery, H2/H3 Recovery,
   H4 Effect Safety, H5 Verification). Write remaining config templates if
   pilot passes.
3. **Paper tables/sections** — figures done; generate the result tables
   (primary contrasts, mechanism matrix, secondary tables) and draft the
   deterministic-evidence sections using the frozen artifacts.
4. **LLM evidence + final writing** — adaptive-agent results, then integrate.

### Discipline (unchanged)

Benchmark semantics are frozen at `aftbench-v1.0-deterministic`. Only
provider-adapter / API-parsing / infrastructure fixes are permitted
thereafter. Never alter verifiers, faults, tasks, treatments, or endpoints
in response to LLM results.
