# AFTBench — Agent Operating Rules

This repository is an **autonomous research artifact**.  All contributors —
human and agent alike — must follow the rules below.

## Hard rules

| # | Rule | Rationale |
|---|------|-----------|
| 1 | **No `sudo`** | The benchmark must run in unprivileged containers and shared VMs. |
| 2 | **No network exfiltration** | No outbound HTTP/SSH except to explicitly whitelisted endpoints (model APIs declared in config). |
| 3 | **No credential commits** | Never commit API keys, tokens, passwords, or private keys.  Use environment variables or `.env` (gitignored). |
| 4 | **Deterministic runs preferred** | Given the same seed and config, a run must be reproducible.  Use `BenchmarkConfig.seed` and avoid wall-clock or hostname-dependent logic in evaluation paths. |
| 5 | **All writes inside the repo** | Every file written by the benchmark or its agents must land under the repository root (`/mnt/f/AFTBench/`).  The sole exception is the configured `output_dir` when it points elsewhere by explicit user choice. |
| 6 | **No destructive git operations** | No `git push --force`, no branch deletion of `main`. |
| 7 | **Tests must pass** | Before committing, run `make acceptance` (or at minimum `make test`). |

## Conventions

- **Python ≥ 3.11**, dataclasses over pydantic, type hints everywhere.
- **One world = one directory** under `src/aftbench/worlds/`.
- **Traces are JSONL** — append-only, one event per line, schema in `schemas.py`.
- **Metrics are pure functions** of `ResultRow` lists — no side effects.
- **Commit messages** follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).

## Agent-specific guidance

- When adding a new world, register it via `@register_world("name")` in `registry.py`.
- When adding a metric, add it to `metrics.py` and include a unit test.
- When modifying schemas, update the JSON Schema export in `schemas.py`.
- Keep the smoke profile runnable in < 60 seconds on a laptop.
