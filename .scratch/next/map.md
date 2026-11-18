# Build NEXT through bounded Shots

Label: wayfinder:map
Status: open

## Destination

A dependency-ordered sprint plan for [NEXT.md](../../NEXT.md), with one
verifiable deliverable per planned Shot and explicit decision gates before
implementation. The delivery schedule is [Shots and sprints](spec.md).

## Notes

This is the local Markdown tracker described by the wayfinder skill. Use
`/setup-matt-pocock-skills` if a different tracker should be configured later.
No external tracker is required for this plan.

The user's request for a Shots/sprints plan permits charting future execution
work in the linked schedule. It does not resolve decision tickets or execute
implementation. Tickets remain questions; the schedule holds build deliverables.

NEXT owns requirements. This map owns navigation. Decision tickets own answers.
The sprint plan owns ordering, scoped deliverables, and proof. Use
`writing-for-agents` for contract edits and the relevant owner context before
implementation. Use `grilling` and `domain-modeling` when a ticket requires a
live user decision; do not substitute an agent's recommendation for their answer.

Existing constraints inherited from NEXT: deepen Repo Context; Genesis owns
selection; Tokens QA owns evidence; retain negative outcomes; human acceptance
remains explicit; compiler/learner evaluation are separate. These are inherited
inputs, not decisions resolved in this charting session.

## Decisions so far

No decision tickets have been resolved in this charting session.

## Not yet specified

- Exact compiler and runner files depend on the selected invocation path.
- The measurable follow-up after first field use depends on actual corrections
  and available telemetry; a rejection is not a prerequisite to invent.
- Domain guards and rail-graph delivery depend on observed failures and actual
  duplicated router decisions. They remain conditional under NEXT stages 7–8.
- A learner experiment's data and evaluation design depend on a useful corpus.

## Out of scope

Publishing, automatic prompt mutation, model training, arbitrary new databases,
and implementation in harness-core. Broad domain activation or adopting Google
ADK is not required to implement NEXT.

## Tracker operations

Tickets are `issues/NN-title.md`. The frontier is open, unassigned tickets whose
`Blocked by` references are all resolved; scan by numeric order. A future
session sets `Status: claimed` and its `Assignee:` before working a ticket.
Resolve by appending `## Answer`, setting `Status: resolved`, and linking its
title under Decisions so far. Resolve at most one non-research ticket per
session. Ticket and Shot identifiers are local planning references, not roadmap
Item IDs or fabricated Shot records.
