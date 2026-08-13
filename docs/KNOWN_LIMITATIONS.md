# Known Limitations

## Scientific Scope

1. **No live LLM results by default**: The benchmark runs with a deterministic scripted agent. Live LLM results require API credentials and are labeled as exploratory when present.

2. **Token proxies**: Token counts for the scripted agent are deterministic proxies based on interface condition and payload size, not actual LLM tokenization. Labeled explicitly in all outputs.

3. **No network modeling**: Wall-clock times measure local computation only. Network latency, queuing, and timeout behavior are not modeled.

4. **Simplified fault timing**: Faults occur at discrete stage boundaries rather than at arbitrary points in continuous time.

## Implementation

5. **Single-process execution**: The benchmark runs sequentially. Parallel task execution is not implemented.

6. **In-memory state**: World state is held in memory. Persistence across process restarts is simulated through serialization but not tested under crash conditions.

7. **No adversarial scenarios**: Catalog distractors and fault patterns are hand-designed, not adversarially generated.

## Paper Alignment

8. **Not all paper claims have evidence**: See `PAPER_REQUIREMENTS_TRACEABILITY.md` for per-claim status. Some claims require live-model experiments not yet performed.

9. **Terminology alignment**: The code uses the paper's terminology (callability, agent-operability, selective discovery, etc.). Obsolete terms are not used.

10. **Statistical power**: With a scripted agent and limited seeds, statistical power is sufficient for large effect sizes but not for subtle differences.
