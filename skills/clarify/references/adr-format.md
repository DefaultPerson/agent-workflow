# ADR format (for /clarify Phase 5 offers)

> Adapted from mattpocock/skills `grill-with-docs/ADR-FORMAT.md` (MIT).

ADRs live in `docs/adr/` with sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.
Create `docs/adr/` lazily — only when the first ADR is written.

## Minimal template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what was decided, and why.}
```

That's it. An ADR can be a single paragraph. The value is recording *that* a decision was made and *why* — not filling out sections.

## Optional sections (only when they add genuine value)

- `Status:` frontmatter (`proposed | accepted | deprecated | superseded by ADR-NNNN`) — useful when decisions are revisited.
- `Considered Options` — only when the rejected alternatives are worth remembering.
- `Consequences` — only when non-obvious downstream effects need to be called out.

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one. Pad to four digits.

```bash
NEXT=$(printf '%04d' "$(( $(ls docs/adr/ 2>/dev/null | grep -oP '^\d+' | sort -n | tail -1 || echo 0) + 1 ))")
```

## When /clarify offers an ADR (all three must be true)

1. **Hard to reverse** — the cost of changing your mind later is meaningful (DB schema, public API contract, infra/auth/messaging choice, security boundary, major dependency lock-in).
2. **Surprising without context** — a future reader looking at just the code will wonder "why on earth did they do it this way?"
3. **Real trade-off** — there were genuine alternatives and you picked one for specific reasons.

If a decision is easy to reverse, skip it — you'll just reverse it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

Cap: maximum 3 ADR offers per /clarify run to prevent fatigue. If more than 3 candidates pass the criteria, surface the 3 with the highest reverse-cost.

## What qualifies (examples)

- **Architectural shape:** "Write model is event-sourced, read model projected into Postgres."
- **Integration patterns between contexts:** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology lock-in choices:** database, message bus, auth provider, deployment target. Not every library — only ones that would take a quarter to swap.
- **Boundary and scope decisions:** "Customer data is owned by the Customer context; other contexts reference by ID only."
- **Deliberate deviations from the obvious path:** "Manual SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite.
- **Constraints not visible in the code:** "No AWS due to compliance." "Response times under 200ms because of partner contract."
- **Rejected alternatives when the rejection is non-obvious:** if you considered GraphQL and picked REST for subtle reasons, record it — otherwise someone will suggest GraphQL again in six months.
