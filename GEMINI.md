# Repository Directives for Autonomous Agents (Gemini)

## 1. Operating Axioms
- NEVER announce completion without a verified exit code 0 from verification and testing tools.
- Never write code directly on protected branches (`main`, `staging`). Work strictly inside assigned Git Worktrees (`.worktrees/task-<id>`).
- Run verification tests after every substantive file change.
- Adhere strictly to the Observe -> Plan -> Act -> Hook -> Verify execution cycle.

## 2. Deterministic Verification Gates
- Unit & Integration Testing: `pytest <target-path> -v`
- Type Checking: `python -m mypy <target-path>` (when enabled)
- Process Exit Code: Process exit code must be strictly `0` for verification pass.

## 3. Memory & Consolidation Directives
- Read architectural constants from `.memory/architecture.md` prior to planning.
- Document any verified edge-case fixes or failure patterns into `.memory/failure-patterns.md`.
- Keep intermediate edits clean; rely on PostToolUse formatters rather than fixing whitespace manually.
- Consolidate new invariants and failure discoveries into `.memory/*.md` during dreaming cycles.
