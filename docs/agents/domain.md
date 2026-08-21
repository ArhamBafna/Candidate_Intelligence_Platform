# Domain Docs

Use this routing before exploring domain behavior.

## Exploration gate

1. Read root `CONTEXT.md` when present.
2. If root `CONTEXT-MAP.md` exists, follow it and read every `CONTEXT.md` relevant to the topic.
3. Read ADRs in `docs/adr/` that touch the target area. In multi-context repos, also read `src/<context>/docs/adr/`.
4. Use glossary terms from the applicable context document in issue titles, refactor proposals, hypotheses, and tests.

Exploration is ready only when every applicable context document and ADR has been checked.

When a referenced file is unavailable, continue with available context. The `/domain-modeling` skill creates missing context documents lazily when terms or decisions are resolved.

## File structure

Single-context repo:

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

Multi-context repo:

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← system-wide decisions
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context-specific decisions
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

If a needed concept is absent from the glossary, treat it as a possible domain gap and note it for `/domain-modeling`; do not silently invent competing terminology.

## Flag ADR conflicts

If proposed work contradicts an ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (event-sourced orders) — but worth reopening because…_
