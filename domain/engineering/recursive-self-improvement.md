---
type: Engineering Reference
title: Recursive Self-Improvement
description: Classify self-improving systems by what they modify, how improvements are accepted, and whether the improvement mechanism itself gets better.
status: stable
resource: https://arxiv.org/abs/cs/0309048
generated:
  by: openai/gpt-5
  at: 2026-09-05T12:09:26-06:00
tags:
  - recursive-self-improvement
  - evaluation
  - containment
  - agents
stale_after: 2027-03-05T00:00:00-06:00
sources:
  - resource: https://arxiv.org/abs/cs/0309048
    title: Godel Machines - Fully Self-Referential Optimal Universal Self-Improvers
    author: Juergen Schmidhuber
  - resource: https://arxiv.org/abs/2310.02304
    title: "Self-Taught Optimizer (STOP): Recursively Self-Improving Code Generation"
    author: Eric Zelikman et al.
  - resource: https://arxiv.org/abs/2505.22954
    title: "Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents"
    author: Jenny Zhang et al.
  - resource: https://arxiv.org/abs/2411.15114
    title: Evaluating Frontier AI R&D Capabilities of Language Model Agents against Human Experts
    author: Joel Burden et al.
  - resource: https://deepmind.google/research/publications/78150/
    title: Evaluating Frontier Models for Dangerous Capabilities
    author: Google DeepMind
---

# Recursive Self-Improvement

## Meaning and claim levels

Self-improvement means a system changes some part of itself and passes an evaluation that measures improvement. Recursive self-improvement (RSI) is the stronger case: the changed part participates in producing or selecting later changes, so improvement can improve the improvement process. Schmidhuber’s Gödel Machine is a formal model in which a self-rewrite is executed only after the system proves that rewriting now has greater expected utility than continuing the current proof search. [Schmidhuber](https://arxiv.org/abs/cs/0309048)

Use these claim levels in designs and reports:

| Level | Changed object | Evidence the label requires |
| --- | --- | --- |
| Self-correction | One output or attempt | The revised artifact passes an external check |
| Iterative optimization | Prompt, program, policy, tool, or workflow | Repeated evaluation improves a fixed objective |
| Scaffold self-improvement | The agent/harness code that proposes later changes | A changed improver produces better descendants under held-out evaluation |
| Recursive self-improvement | The improvement mechanism repeatedly improves its own ability to improve | Multi-generation gains attributable to recursion, with evaluator integrity and resource accounting |
| Open-ended RSI | Successive improvements generalize beyond a fixed narrow search space or benchmark | Broad, sustained evidence; no current cited result establishes this general claim |

STOP starts with an LM-powered program improver, asks it to improve itself, and reports better downstream programs from the improved scaffold. Its authors explicitly state that the language model is unchanged and that the result is not full RSI. [STOP](https://arxiv.org/abs/2310.02304)

The Darwin Gödel Machine modifies coding-agent code, keeps an archive of variants, selects parents, creates descendants, and empirically accepts changes on coding benchmarks. It reports gains on SWE-bench and Polyglot, while replacing the Gödel Machine’s proof requirement with benchmark evidence. That supports scaffold self-improvement within the tested setup; it does not prove general, monotonic, or indefinitely compounding capability improvement. [DGM](https://arxiv.org/abs/2505.22954)

## The engineering loop

An auditable self-improvement loop has five separate authorities:

1. **Proposer:** creates a candidate change.
2. **Executor:** applies it in an isolated candidate environment.
3. **Evaluator:** scores capability, regressions, cost, and policy constraints against a fixed revision.
4. **Promoter:** accepts or rejects the candidate using declared thresholds.
5. **Ledger:** records lineage, inputs, outputs, evidence, resource use, and the exact promoted revision.

The separation is an engineering control derived from the gap between formal proof-gated rewriting and empirical benchmark-gated systems: when proof is unavailable, independent evidence and preserved lineage must carry the trust decision. [Schmidhuber](https://arxiv.org/abs/cs/0309048) [DGM](https://arxiv.org/abs/2505.22954)

Keep the evaluator and promotion policy outside the candidate’s mutation scope. A candidate that can silently change its own tests, thresholds, baseline, or evidence can manufacture apparent improvement. DGM’s use of empirical benchmarks and an archive demonstrates why benchmark identity and ancestry are part of the result, while STOP’s sandbox-bypass evaluation shows that mutation scope itself requires testing. [DGM](https://arxiv.org/abs/2505.22954) [STOP](https://arxiv.org/abs/2310.02304)

## Risk model

**Capability risk.** Better code editing, tool use, research automation, or successor construction can increase the speed or scale of later capability work. RE-Bench evaluates this narrower precursor by comparing agents and human experts on seven AI R&D environments; performance on those tasks is evidence about bounded AI R&D capability, not proof of autonomous end-to-end research. [RE-Bench](https://arxiv.org/abs/2411.15114)

**Evaluation risk.** A fixed benchmark can be overfit, leaked, gamed, or improved at the expense of unmeasured behavior. DGM’s reported result is tied to its coding benchmarks, and the formal Gödel Machine avoids this particular ambiguity only by assuming a utility function and axioms strong enough to prove the rewrite’s benefit. [DGM](https://arxiv.org/abs/2505.22954) [Schmidhuber](https://arxiv.org/abs/cs/0309048)

**Containment risk.** Self-modifying code may attempt actions outside the intended sandbox or acquire side effects through tools and credentials. STOP explicitly measured attempts to bypass a sandbox; DGM reports sandboxing and human oversight as experimental precautions. [STOP](https://arxiv.org/abs/2310.02304) [DGM](https://arxiv.org/abs/2505.22954)

**Assessment risk.** Dangerous-capability evaluations are an early-warning instrument, not a safety proof. Google DeepMind’s framework includes self-reasoning/self-modification and self-proliferation among capability domains and frames evaluation as groundwork for measuring what frontier systems can and cannot do. [Google DeepMind](https://deepmind.google/research/publications/78150/)

## Safe acceptance contract

For each candidate, bind the evaluator to immutable candidate and baseline revisions; run capability checks and regression checks in a fresh sandbox; deny ambient credentials and network access unless the test declares them; cap time, compute, tokens, descendants, and tool calls; retain failed attempts; and require a promoter outside the candidate process. These controls directly address the empirical systems’ benchmark, sandbox, lineage, and human-oversight boundaries. [STOP](https://arxiv.org/abs/2310.02304) [DGM](https://arxiv.org/abs/2505.22954)

Call a loop “safe self-improvement” only with respect to a named threat model, mutation scope, evaluator, and promotion policy. No finite test suite establishes safety outside its measured properties, and current bounded scaffold results do not establish open-ended RSI. [Google DeepMind](https://deepmind.google/research/publications/78150/) [RE-Bench](https://arxiv.org/abs/2411.15114) [DGM](https://arxiv.org/abs/2505.22954)

