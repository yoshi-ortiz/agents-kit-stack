# Choose package-check ownership

Parent: [Build NEXT through bounded Shots](../map.md)
Label: wayfinder:task
Type: task
Mode: AFK
Status: open
Assignee: unassigned
Blocked by: none

## Question

Which existing checks enforce generic package policy, which require Aesthetic,
and where can they move without creating a second discovery registry?

## Proposal to evaluate

Inventory actual callers and classify behavior before choosing file destinations.
Reuse Tools discovery and retain skill-specific checks behind their own entrypoints.

## Read when claimed

Perform read-only tracing of check.py, release.py, publish.py, fog.py,
contracts.py and bootstrap_harness.py. Attach a compact caller/ownership table.

## Resolution evidence

The prerequisite inventory is complete when every proposed moved check has a
current caller, destination owner and behavior-preservation proof. Append the
result as the resolution; code extraction belongs to the sprint plan.

## Comments

Charted only. No answer or user decision has been recorded.

