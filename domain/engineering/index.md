# Engineering knowledge

Use this bundle to choose boundaries and evidence for agent-assisted engineering systems. Load one concept at a time; the terms overlap in ordinary speech but carry different authority and failure modes here.

| Concept | Purpose | Trust boundary |
| --- | --- | --- |
| [Vertical Slice Architecture](vertical-slice-architecture.md) | Decide whether code should follow a feature/use-case boundary or a technical layer, and where dependencies may cross. | Practitioner pattern from its named proponent, reconciled with the Clean Architecture dependency rule; useful design guidance, not a formal standard. |
| [Recursive Self-Improvement](recursive-self-improvement.md) | Classify a claimed self-improvement loop, set evidence requirements, and choose containment boundaries. | Formal research plus bounded empirical systems and first-party evaluations; benchmark gains do not establish open-ended or generally safe RSI. |
| [LLM Reinforcement Learning](llm-reinforcement-learning.md) | Distinguish RL training from preference collection, feedback logging, inference-time search, and deterministic orchestration. | Original methods papers and the standard RL definition; empirical claims hold only for the cited training setup and evaluation distribution. |
| [Harness, Loop, Graph Engineering, and Google ADK](harness-loop-graph-google-adk.md) | Place runtime control, state, tools, workflow edges, and policy gates in an agent system. | First-party engineering guidance and current Google ADK documentation/source; product APIs are version-bound and must be rechecked after `stale_after`. |

## Collision guide

- A **slice** is a code ownership boundary around one use case.
- A **harness** supplies an agent's execution environment and operational controls.
- A **loop** repeats observe-decide-act until a stop condition.
- A **graph** makes allowed transitions and joins explicit.
- **Feedback** is recorded evidence; it becomes **reinforcement learning** only when a learning algorithm uses reward-derived signal to update a policy.
- **Self-improvement** is any measured improvement to a system component; **recursive self-improvement** additionally improves the mechanism that produces later improvements.

