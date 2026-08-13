# AFTBench

**Behavioral Contracts and Controlled Evaluation for Agent-First Tooling**

AFTBench is a benchmark suite for evaluating AI-agent tooling systems along
multiple axes: correctness, safety, fault recovery, efficiency, and overhead.
It provides a structured framework of *worlds* (simulated environments),
*interfaces* (tool APIs), *agents* (systems under test), *verifiers*
(automated checkers), and *fault injectors* — all orchestrated through
configurable run profiles.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   CLI / API                      │
├──────────┬──────────┬──────────┬────────────────┤
│  Worlds  │Interfaces│  Agents  │   Verifiers    │
│ (envs)   │ (tools)  │ (SUTs)   │  (checkers)    │
├──────────┴──────────┴──────────┴────────────────┤
│              Fault Injection Layer               │
├─────────────────────────────────────────────────┤
│         Trace Writer  ·  Metrics Engine          │
├─────────────────────────────────────────────────┤
│          Analysis  ·  Report Generation          │
└─────────────────────────────────────────────────┘
```

### Key components

- **Worlds** — simulated environments (filesystem, database, web, …)
- **Interfaces** — tool catalogs exposed to agents
- **Agents** — systems under test (LLM-based, rule-based, oracle, …)
- **Verifiers** — check postconditions, safety predicates, state correctness
- **Faults** — injectable failures (latency, errors, schema drift, …)
- **Traces** — JSONL event logs for every run
- **Metrics** — 30+ metrics covering correctness, safety, recovery, efficiency

## Setup

```bash
# Clone and enter the repo
cd AFTBench

# Create virtual environment and install dependencies
make setup

# Activate the environment
source .venv/bin/activate
```

## Running

```bash
# Quick sanity check (< 60 s)
make smoke

# Small-scale evaluation
make pilot

# Full ablation suite
make ablations

# Compute metrics from latest results
make analyze

# Generate report (tables + figures)
make report

# Full acceptance gate (lint + typecheck + test + smoke + analyze)
make acceptance
```

### Profiles

| Profile     | Purpose                          | Typical duration |
|-------------|----------------------------------|------------------|
| `smoke`     | Fast sanity check                | < 1 min          |
| `pilot`     | Small-scale evaluation           | 5–15 min         |
| `full`      | Complete benchmark run           | 1–4 hours        |
| `ablations` | Factor-by-factor ablation suite  | 2–6 hours        |

## Configuration

Runs are configured via YAML files in `configs/`.  A minimal config:

```yaml
profile: smoke
seed: 42
output_dir: artifacts/smoke
max_tasks: 5
max_turns: 10
cost_limit: 1.00
```

See `src/aftbench/config.py` for the full schema.

## Documentation

Detailed documentation lives in [`docs/`](docs/):

- [Worlds](docs/worlds.md) — how to create and register new worlds
- [Metrics](docs/metrics.md) — full metric definitions and formulas
- [Fault Model](docs/faults.md) — fault types and injection schedules
- [Agent Protocol](docs/agents.md) — how to integrate a new agent

## Development

```bash
# Run tests
make test

# Lint
make lint

# Type-check
make typecheck
```

## License

MIT — see [LICENSE](LICENSE).
