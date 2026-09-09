# Known Failure Patterns & Regressions

This document is maintained by the Dreaming Engine to record resolved bugs and prevent regressions.

## FP-014: Concurrent Worker Deadlocks on Shared SQLite Mocks
- **Date:** 2026-09-05
- **Symptoms:** Test suite hangs indefinitely when running concurrent test workers.
- **Root Cause:** In-memory SQLite (`:memory:`) cannot be safely accessed across concurrent worker processes without file backing.
- **Rule:** Always use dynamic per-worker temporary database files (`.tmp/test-${workerId}.db`) and clean up in test teardowns.

## FP-021: Missing Refresh Token Cookie Path Restriction
- **Date:** 2026-09-07
- **Symptoms:** Refresh tokens were transmitted to unrelated subpaths, failing security audit checks.
- **Rule:** Refresh token cookies must explicitly specify `Path=/api/v1/auth/refresh`, `HttpOnly=true`, and `SameSite=Strict`.

## FP-035: False Sequential Edges in Worker DAGs
- **Date:** 2026-09-08
- **Symptoms:** Independent worker tasks executing sequentially, resulting in 4x total latency.
- **Root Cause:** Specifying node dependency without actual data artifact exchange.
- **Rule:** Workers without shared file/artifact dependencies must have false edges pruned for parallel execution.
