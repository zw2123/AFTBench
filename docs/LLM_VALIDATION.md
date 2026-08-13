# LLM Ecological Validation — Setup & Design

Deterministic evidence (v1.0 freeze, tag `aftbench-v1.0-deterministic`) has
established that AFT primitives causally eliminate specific operational
failure modes.  This phase asks the remaining question:

> Do real adaptive agents *use* these mechanisms when exposed to them?

## 1. Credentials: one `.env` file

All API keys live in a **single file**: `.env` at the repository root.

- Path: `/mnt/f/AFTBench/.env`
- Format: standard `KEY=VALUE`, one per line
- It is **gitignored** — never committed.  `.env.example` is the committed
  template (copy it: `cp .env.example .env`).

```
AFTBENCH_API_KEY_QWEN=sk-...
AFTBENCH_API_KEY_DEEPSEEK=sk-...
AFTBENCH_API_KEY_SOL=sk-...
```

The loader (`src/aftbench/llm/env.py`) reads `.env` into the environment at
runtime without overriding already-set variables, so you can also export
these vars in your shell instead.

**Why one file?** Simpler to manage than three separate files, and the
secrets are never in git.  What *is* tracked is `configs/llm/providers.yaml`
— non-secret metadata (endpoints, pricing, which env var to use).

## 2. Provider profiles: `configs/llm/providers.yaml` (tracked)

```yaml
providers:
  qwen-3.7-plus:
    api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
    api_key_env: AFTBENCH_API_KEY_QWEN
    input_price_per_1k: 0.0008
    output_price_per_1k: 0.0024
    max_tokens: 4096
```

Rules:
- The top-level key (`qwen-3.7-plus`) is the model id sent in the request
  and the value used by `llm_model:` in benchmark configs.
- `api_key_env` names the `.env` variable holding the key — never put the
  key in this file.
- Any OpenAI-compatible chat-completions endpoint works out of the box
  (Qwen/DashScope, DeepSeek, OpenAI, local vLLM servers).
- To add a provider: add a block here + a line in `.env`.

## 3. Architecture

```
src/aftbench/llm/
├── env.py               # .env loader (no external dep)
├── base.py              # LLMProvider ABC + LLMResponse
├── openai_compatible.py # urllib-based OpenAI-compatible client
└── registry.py          # profiles.yaml loader + get_provider()

src/aftbench/agents/optional_llm.py   # LLMAgent using the registry
```

The agent is disabled by default: it activates only when the benchmark
config sets `agent: llm` **and** the profile's API key is present.  Without
a key it logs a warning and falls back to the capability-aware agent, so
existing deterministic runs are unaffected.

## 4. Running a pilot

```bash
python -m aftbench run --config configs/llm/pilot_qwen.yaml
```

The pilot mirrors the deterministic H5 workload (I5 vs I5-minus-verification
under `false_success`) so the adaptive agent's terminal claims can be
compared against the deterministic mechanism (I5 corrects, minus-verification
does not).

## 5. Planned matrix (after pilot)

| Hypothesis | Primitive | Workload | Config template |
|-----------|-----------|----------|-----------------|
| H1 Discovery | selective discovery | discovery_frontier | `configs/evidence/discovery_frontier.yaml` |
| H2/H3 Recovery | resume / durable state | interruption_recovery | `configs/evidence/interruption_recovery.yaml` |
| H4 Effect Safety | effect contracts | stale_permission / postcommit_loss | `configs/evidence/...` |
| H5 Verification | verification | verification / verification_partial | `configs/evidence/verification.yaml` |

Three models: `qwen-3.7-plus`, `deepseek-v4-pro`, `gpt-5.6-sol`.

## 6. Freeze discipline

Benchmark semantics are frozen at `aftbench-v1.0-deterministic`.  During LLM
validation, only these fixes are permitted:
- provider adapter bugs (endpoint/header/response parsing)
- API parsing bugs
- infrastructure failures

**Never** change verifiers, faults, tasks, treatments, or endpoints in
response to LLM results.  If an LLM underperforms on I5, that is an
ecological finding about the agent, not a reason to alter the benchmark.
