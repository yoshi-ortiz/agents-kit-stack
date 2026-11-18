# Choose feedback history and closure concurrency

Parent: [Build NEXT through bounded Shots](../map.md)
Label: wayfinder:grilling
Type: grilling
Mode: HITL
Status: open
Assignee: unassigned
Blocked by: 01

## Question

What is the smallest event representation and concurrency protocol that preserves
feedback history, supports idempotent writes, and detects a stale closure?

## Proposal to evaluate

Compare extending the existing Shot storage with per-Shot immutable events
against a separate event stream. Keep observation identity stable, use explicit
operation IDs and expected revisions, and specify legacy provenance as unknown.

## Read when claimed

Read Tokens QA schema/I/O/feedback/history and the chosen Item contract.
Walk two concurrent verdict writes, correction resolution and a new latest Shot.

## Resolution evidence

The answer fixes event identity/order, effective-verdict reduction, conflict
behavior, legacy read policy, closure revalidation and redaction/deletion effects.
User confirmation is required; no storage implementation is part of resolution.

## Comments

Charted only. No answer or user decision has been recorded.
