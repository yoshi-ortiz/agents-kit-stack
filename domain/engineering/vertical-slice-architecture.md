---
type: Architecture Pattern
title: Vertical Slice Architecture
description: Organize a system around independently changeable use cases while keeping dependency rules explicit at shared boundaries.
status: stable
resource: https://www.jimmybogard.com/vertical-slice-architecture/
generated:
  by: openai/gpt-5
  at: 2026-09-05T12:09:26-06:00
tags:
  - architecture
  - modularity
  - vertical-slice
  - clean-architecture
sources:
  - resource: https://www.jimmybogard.com/vertical-slice-architecture/
    title: Vertical Slice Architecture
    author: Jimmy Bogard
  - resource: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
    title: The Clean Architecture
    author: Robert C. Martin
---

# Vertical Slice Architecture

## Working definition

A vertical slice groups the code needed to fulfill one request or use case, from its entry point through validation, domain behavior, persistence, and response shape. The unit of cohesion is the change: code that usually changes together lives together, coupling is high inside the slice, and coupling between slices is kept low. This is the pattern Jimmy Bogard named “Vertical Slice Architecture.” [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)

Treat the name as practitioner vocabulary. Bogard presents an architectural style learned from project work, not a standards-body specification or a uniquely defined package layout. A repository conforms by preserving use-case cohesion and slice independence, not by adopting MediatR, CQRS, request handlers, or a particular framework. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)

## Dependency direction

Feature-local organization answers **what changes together**. Dependency direction answers **what is allowed to know what**. Clean Architecture’s dependency rule says source dependencies point inward toward higher-level policy and that inner code does not name outer mechanisms. [Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

These choices operate on different axes and can coexist:

| Decision | Vertical slice answer | Clean/layered answer |
| --- | --- | --- |
| Primary module boundary | One request or use case | One technical responsibility or policy ring |
| Local implementation | Tailored to the slice | Usually follows a system-wide layer protocol |
| Shared policy | Extract only after real cross-slice pressure | Place toward the inner policy boundary |
| Infrastructure | May sit beside slice code behind a narrow seam | Lives outside and depends inward |

Bogard explicitly contrasts slices with system-wide layered gates such as controller → service → repository, while Martin’s rule constrains dependencies across policy boundaries. A slice can therefore contain thin delivery and persistence adapters while its durable business rules remain independent of those adapters. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/) [Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## Engineering placement rule

Start a feature in one slice. Keep its request/command, validation, orchestration, persistence query or adapter, response model, and focused tests close enough to inspect as one change. Promote code to a shared module only when multiple slices already require the same policy and the shared dependency has a stable meaning. This follows Bogard’s direction to maximize cohesion within a slice and minimize coupling across slices. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)

Use a domain module when behavior must stay consistent across several slices or when a business invariant has a lifecycle beyond one request. The outer slice may orchestrate that domain behavior; the domain must not depend on transport, UI, database, or framework details under the Clean Architecture dependency rule. [Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## Review checklist

- Can an engineer describe the user-visible use case by reading one slice?
- Does a typical feature change remain inside one slice plus deliberately shared policy?
- Are cross-slice calls explicit, or do slices reach into one another’s internals?
- Did a shared abstraction emerge from repeated policy, or was it created to enforce a generic layer sequence?
- Do durable rules depend inward while delivery and persistence mechanisms depend on them?

The checklist operationalizes the two source rules: couple along the axis of change and point dependencies toward policy. It is a project convention, not an independently standardized conformance test. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/) [Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

## Common failures

**Folders renamed, coupling unchanged.** A `Features/` directory is cosmetic when handlers still route through shared services that own every decision. Slice autonomy comes from ownership of the use-case flow, not the directory name. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)

**Cross-slice duplication removed too early.** Small repeated mechanics may be cheaper than a shared abstraction that couples unrelated changes. Bogard’s design keeps cross-slice sharing minimal and lets patterns emerge through refactoring. [Bogard](https://www.jimmybogard.com/vertical-slice-architecture/)

**Business policy trapped in an endpoint.** Slice locality does not excuse coupling durable policy to HTTP, UI, or storage. When a rule serves multiple operations, move that rule inward and leave each slice responsible for its own orchestration. [Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

