---
type: Engineering Reference
title: Harness, Loop, Graph Engineering, and Google ADK
description: Place agent execution, iteration, workflow transitions, state, tools, and policy controls in a runtime with explicit authority boundaries.
status: stable
resource: https://github.com/google/adk-docs/blob/main/docs/runtime/event-loop.md
generated:
  by: openai/gpt-5
  at: 2026-09-05T12:09:26-06:00
tags:
  - agent-harness
  - agent-loop
  - workflow-graph
  - google-adk
stale_after: 2027-03-05T00:00:00-06:00
sources:
  - resource: https://openai.com/index/harness-engineering/
    title: "Harness engineering: leveraging Codex in an agent-first world"
    author: OpenAI
  - resource: https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
    title: A practical guide to building agents
    author: OpenAI
  - resource: https://www.anthropic.com/engineering/building-effective-agents
    title: Building effective agents
    author: Anthropic
  - resource: https://github.com/google/adk-docs/blob/main/docs/runtime/event-loop.md
    title: Runtime and Event Loop
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/sessions/session/index.md
    title: Sessions and SessionService
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/sessions/state.md
    title: Session state
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/tools-custom/index.md
    title: Custom tools
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/tools-custom/mcp-tools.md
    title: MCP tools
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md
    title: Types of callbacks
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/agents/workflow-agents/index.md
    title: Workflow agents
    author: Google
  - resource: https://github.com/google/adk-docs/blob/main/docs/graphs/index.md
    title: Graph-based agent workflows
    author: Google
  - resource: https://github.com/google/adk-python/blob/main/src/google/adk/runners.py
    title: Google ADK Python Runner source
    author: Google
---

# Harness, Loop, Graph Engineering, and Google ADK

## Four different objects

A **runtime harness** is the software around a model that supplies instructions, context, tools, credentials, isolation, persistence, observability, budgets, and acceptance gates. OpenAI’s harness engineering account treats repository legibility, standard tools, isolated worktrees, browser control, logs, metrics, and iterative review as infrastructure that enables an agent to complete useful work. [OpenAI harness engineering](https://openai.com/index/harness-engineering/)

An **agent loop** is the runtime cycle that receives an objective and state, lets a model choose an action, executes a tool or emits an answer, observes the result, and repeats until a stop condition. OpenAI’s implementation guide describes a run as a loop and recommends starting with a single agent before adding orchestration complexity; Anthropic likewise separates fixed workflows from agents whose models dynamically direct their process and tool use. [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) [Anthropic](https://www.anthropic.com/engineering/building-effective-agents)

A **workflow graph** is an explicit control model: nodes perform work, edges constrain possible transitions, joins combine branches, and terminal nodes end the run. A graph may contain deterministic nodes, model-driven agents, tools, or functions. Google ADK 2.0 documents graph workflows as nodes and edges with explicit routing, alongside dynamic workflows and prebuilt sequential, parallel, and loop agents. [Google graph workflows](https://github.com/google/adk-docs/blob/main/docs/graphs/index.md) [Google workflow agents](https://github.com/google/adk-docs/blob/main/docs/agents/workflow-agents/index.md)

**Harness engineering**, **loop engineering**, and **graph engineering** are practice terms rather than interoperable standards. Use them to name the controlled layer: harness for operational capability and policy, loop for repeated action and stopping, graph for allowed ordering and branching. The concrete contract comes from the selected runtime and application, not the label. [OpenAI harness engineering](https://openai.com/index/harness-engineering/) [Anthropic](https://www.anthropic.com/engineering/building-effective-agents)

## Google ADK runtime map

Context7 was queried successfully on 2026-09-05 using the official high-reputation library `/google/adk-docs`; the citations below point to Google’s documentation and source of record.

| ADK concept | Owns | Keep outside it |
| --- | --- | --- |
| `Agent` / `LlmAgent` | Instructions, model behavior, tool declarations, delegation behavior | Durable session storage and global promotion policy |
| `Runner` | Invocation lifecycle, event consumption, coordination with session/artifact/memory/credential services | Product-specific acceptance truth |
| `Session` + `SessionService` | Conversation events and scoped state persistence | Secrets or evidence whose retention policy differs from conversation state |
| `Tool` + `ToolContext` | A bounded side effect or query plus invocation-scoped state/auth facilities | Unreviewed ambient authority |
| Callbacks | Observation, guard checks, input/output transformation, and documented short-circuit points | A hidden second workflow that duplicates graph logic |
| Graph `Workflow` | Explicit nodes, edges, routes, joins, and typed handoffs in ADK 2.0 | Policy hidden in long prompts or mutable session keys |
| Workflow agents | Deterministic sequential, parallel, or repeated sub-agent execution | Unbounded iteration without an external budget and termination policy |

The ADK `Runner` is the execution boundary that runs an agent and yields events. In the event loop, agents, tools, and callbacks cooperatively yield events; the Runner commits state-changing events through the session service before execution resumes, so resumed logic can observe committed state. [Google event loop](https://github.com/google/adk-docs/blob/main/docs/runtime/event-loop.md) [Runner source](https://github.com/google/adk-python/blob/main/src/google/adk/runners.py)

A `Session` holds the event history and state for a user/application/session identity, while `SessionService` selects the storage implementation. Google documents the in-memory implementation as ephemeral and intended for development or testing, which makes the service choice part of the durability boundary. [Google sessions](https://github.com/google/adk-docs/blob/main/docs/sessions/session/index.md)

State writes through callback or tool context become event state deltas that the session service applies. ADK uses key prefixes to distinguish application, user, session, and temporary state scopes, so state key naming is an authority and lifetime decision rather than a cosmetic convention. [Google state](https://github.com/google/adk-docs/blob/main/docs/sessions/state.md) [Google custom tools](https://github.com/google/adk-docs/blob/main/docs/tools-custom/index.md)

A tool is the narrow place to expose an external capability. `ToolContext` provides invocation-bound state and service access; direct calls made with `tool_context=None` do not carry the full Runner-provided state/auth context, so code that requires those facilities belongs in a Runner invocation or must receive an explicit substitute. [Google MCP tools](https://github.com/google/adk-docs/blob/main/docs/tools-custom/mcp-tools.md)

## Control points

Place hard authorization before the side effect. ADK’s `before_tool_callback` can inspect a requested tool call and return a result that bypasses normal tool execution; `before_model_callback` can return a model response that bypasses the model call. These are suitable enforcement seams for allowlists, budgets, argument validation, and cached/denied responses. In Python, ADK passes callback arguments by keyword, so parameter names must match the documented names such as `callback_context` and `tool_context`; aliases can fail at runtime with `TypeError`. [Google callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)

Use after-callbacks for observation, normalization, evidence capture, and checks that can reject a result before promotion. Do not rely on an after-callback to prevent an external side effect that already happened; the authorization decision belongs before the tool invocation. The callback positions and bypass behavior are defined by ADK’s callback contract. [Google callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)

Use an ADK 2.0 graph `Workflow` when nodes, routes, joins, and typed handoffs need explicit review. Use `SequentialAgent` when every child must run in order, `ParallelAgent` when independent branches can run concurrently, and `LoopAgent` for bounded repetition with a declared stop signal. Google documents graph, dynamic, and prebuilt workflow styles as complementary choices; each keeps declared control flow outside model judgment. [Google graph workflows](https://github.com/google/adk-docs/blob/main/docs/graphs/index.md) [Google workflow agents](https://github.com/google/adk-docs/blob/main/docs/agents/workflow-agents/index.md)

## Practical architecture

Keep one authoritative ledger of run, step, tool call, result, evidence, and final verdict. Let ADK session events carry conversational/runtime state, and copy only the evidence required by the product’s audit and promotion contract into its durable store. This respects the Runner’s event semantics while avoiding the assumption that a conversation store is automatically an acceptance ledger. [Google event loop](https://github.com/google/adk-docs/blob/main/docs/runtime/event-loop.md) [Google sessions](https://github.com/google/adk-docs/blob/main/docs/sessions/session/index.md)

Bound every loop with iteration, wall-time, token, cost, and side-effect limits; make terminal states explicit; preserve the last committed event and stop reason. OpenAI’s guide makes the run loop the core orchestration primitive, while ADK exposes events and workflow agents as the concrete execution controls. [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) [Google event loop](https://github.com/google/adk-docs/blob/main/docs/runtime/event-loop.md) [Google workflow agents](https://github.com/google/adk-docs/blob/main/docs/agents/workflow-agents/index.md)

Use graph structure for reviewable policy: explicit nodes for proposal, execution, verification, human approval, and promotion make skipped gates visible. Use callbacks for cross-cutting controls at model/tool boundaries and tools for individual capabilities. This division follows ADK’s documented ownership of graph routing, callback interception, and tool execution. [Google graph workflows](https://github.com/google/adk-docs/blob/main/docs/graphs/index.md) [Google callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md) [Google custom tools](https://github.com/google/adk-docs/blob/main/docs/tools-custom/index.md)

## Failure modes

- **Loop disguised as learning:** retries alter transient context but never update a policy. Call it inference or orchestration. [OpenAI guide](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf)
- **Graph encoded in callbacks:** ordering becomes implicit and difficult to replay. Put transitions in a graph `Workflow` or prebuilt workflow agent, and reserve callbacks for lifecycle controls. [Google graph workflows](https://github.com/google/adk-docs/blob/main/docs/graphs/index.md) [Google workflow agents](https://github.com/google/adk-docs/blob/main/docs/agents/workflow-agents/index.md) [Google callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)
- **Session treated as authorization:** persisted state records context but does not itself grant permission. Check authority at the tool boundary. [Google state](https://github.com/google/adk-docs/blob/main/docs/sessions/state.md) [Google callbacks](https://github.com/google/adk-docs/blob/main/docs/callbacks/types-of-callbacks.md)
- **In-memory state treated as durable:** process restart loses the documented in-memory session data. Select a persistent `SessionService` for recovery requirements. [Google sessions](https://github.com/google/adk-docs/blob/main/docs/sessions/session/index.md)
- **Bypassing Runner context:** a direct tool call with no context loses Runner-provided state/auth facilities. Use an invocation or pass narrowly scoped dependencies explicitly. [Google MCP tools](https://github.com/google/adk-docs/blob/main/docs/tools-custom/mcp-tools.md)
