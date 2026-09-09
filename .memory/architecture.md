# Architecture Invariants & System Constants

*Last Updated by Agent Dreaming Engine: 2026-09-08 (Task: task-auth-v2)*

## Data Storage & Caching
- **Session Store:** Session tokens must be persisted using atomic Redis transactions (`MULTI/EXEC`). In-memory mock stores fail under concurrent test workers.
- **Database Transactions:** Wrap all balance adjustments and critical mutations in explicit transactions with Serializable isolation where supported.

## Inter-Service Communication
- **Internal APIs:** All internal service RPCs require an `x-correlation-id` header passed from the initial API Gateway request.
- **Error Payloads:** Standardize all service error payloads to `{ "error": { "code": string, "message": string, "details": any } }`.

## Concurrency & Worktrees
- **Isolation Scope:** Every parallel worker MUST operate inside its designated `.worktrees/task-<id>` path on its dedicated `agent/<id>` branch.
- **Direct Commits:** Autonomous agents must never commit or rebase directly onto protected branches (`main`, `staging`).
