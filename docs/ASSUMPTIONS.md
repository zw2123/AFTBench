# Assumptions

This document records assumptions made during autonomous construction of AFTBench.

## Data Generation

- All benchmark data is synthetically generated. No real user data is used.
- Contact names, account names, and ticket IDs are fictional.
- Tool catalog descriptions are generated to be realistic but do not correspond to real APIs.

## Agent Behavior

- The scripted agent uses keyword matching and predefined workflows, not learned policies.
- Token counts for the scripted agent are deterministic proxies based on interface condition, not actual LLM tokenization.
- The scripted agent is intentionally non-omniscient: it discovers tools through the interface like a real agent would.

## Statistical Analysis

- Bootstrap confidence intervals use 1000 resamples with a fixed seed (42).
- Paired comparisons require matching (task, world, fault, seed, agent) tuples.
- Missing pairs are reported explicitly, not silently dropped.

## Interface Parity

- All interface conditions I0–I5 operate on the same backend world operations.
- Stronger interfaces expose more contract metadata but do not provide hidden task answers.
- The verifier can inspect state but cannot mutate it.

## Fault Injection

- Faults are deterministic given a seed.
- The fault oracle records ground truth independently of the agent's perception.
- Lost-response-after-effect faults commit the backend change before dropping the response.

## Limitations

- No live LLM results are included unless explicitly labeled as exploratory.
- Token proxies are labeled as such and computed consistently across interfaces.
- The benchmark does not model network latency; wall_clock_ms measures only local computation.
