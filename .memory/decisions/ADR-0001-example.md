# ADR-0001: Atomic Redis Session Store Migration

## Status
Accepted

## Context
During high-concurrency worker execution, in-memory session synchronization produced transient race conditions in the Auth service.

## Decision
Migrate from local memory maps to Redis-backed distributed sessions using Redis pipeline transactions.

## Consequences
- Requires Redis instance availability during integration test runs.
- Guarantees thread-safe token revocation across multiple worker worktrees.
