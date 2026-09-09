# Markdown Memory Specification & Governance

This directory (`.memory/`) serves as the permanent, human-readable semantic memory repository for autonomous agents operating within the AgentGraph harness.

## Memory Organization

- **`architecture.md`**: System invariants, cross-cutting rules, schema contracts, and architectural constants.
- **`failure-patterns.md`**: Discovered anti-patterns, edge cases, root causes, and prevention rules.
- **`conventions.md`**: Code style, testing structures, naming standards, and fixture locations.
- **`decisions/`**: Architecture Decision Records (ADRs) capturing major design choices.

## Distillation Rules

1. **Human Auditable**: All memory entries must remain in clean, standard Markdown format with git-diffable sections.
2. **Selective Forgetting**: Ephemeral logs and raw stack traces are discarded during dreaming; only durable patterns are stored here.
3. **Traceability**: Memory items must link to their originating task ID or git commit reference.
