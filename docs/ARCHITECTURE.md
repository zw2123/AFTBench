# Architecture

## Overview

AFTBench is a deterministic benchmark for evaluating agent-first tooling interfaces. It measures how interface contracts (I0–I5) affect agent correctness, safety, and efficiency across four benchmark worlds.

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                    CLI (cli.py)                      │
├─────────────────────────────────────────────────────┤
│                 Runner (runner.py)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  Agent   │  │Interface │  │  Fault Injector   │  │
│  │ (agents/)│  │(interfaces/)│  │   (faults/)     │  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
│       │              │                  │            │
│       └──────────────┼──────────────────┘            │
│                      │                               │
│              ┌───────┴───────┐                       │
│              │    World      │                       │
│              │  (worlds/)    │                       │
│              └───────┬───────┘                       │
│                      │                               │
│              ┌───────┴───────┐                       │
│              │   Verifier    │                       │
│              │ (verifiers/)  │                       │
│              └───────────────┘                       │
├─────────────────────────────────────────────────────┤
│              Trace / Metrics / Analysis              │
│  (trace.py, metrics.py, analysis/)                   │
└─────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Interface Ladder (I0–I5)
Each interface condition is cumulative:
- **I0**: Legacy CRUD/RPC baseline
- **I1**: + Schema normalization
- **I2**: + Selective discovery
- **I3**: + Lifecycle awareness
- **I4**: + Effect contracts
- **I5**: + Full AFT (durable state, reconciliation, evidence)

### Backend Parity
All interfaces operate on the same backend `World` operations. The interface layer adds contract metadata without changing backend semantics.

### Deterministic Scripted Agent
The default agent uses keyword matching and fixed policies, enabling CI-runnable benchmarks without LLM API costs.

### Fault Injection with Oracle
Faults are injected at defined boundaries. An independent oracle tracks ground truth (commit status, response delivery, etc.) separate from the agent's perception.

### State-Based Verification
Post-execution verification checks actual world state, not just agent claims. This distinguishes true success from false-success claims.

## Data Flow

1. **Config** → determines (tasks × interfaces × faults × seeds)
2. **Runner** → for each combination:
   a. Reset world to deterministic initial state
   b. Agent discovers tools through interface
   c. Agent selects tool and builds parameters
   d. Interface invokes backend (with fault injection)
   e. Agent handles response/error
   f. Verifier checks final state
   g. Metrics computed
3. **Results** → CSV with one row per run
4. **Traces** → JSONL with all events
5. **Analysis** → paired comparisons, bootstrap CIs
6. **Report** → Markdown summary with plots
