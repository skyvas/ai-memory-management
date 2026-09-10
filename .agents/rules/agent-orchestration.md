# Agent Orchestration & Autonomous Execution Directives

## 1. Operating Axioms & Deterministic Verification
- **Binary Ground Truth:** NEVER announce completion without a verified process exit code `0` from external compilers and test runners (`pytest`, `mypy`, `ruff`, etc.). Subjective natural language assertions ("I have implemented and verified this") are unverified claims.
- **Heartbeat Execution Cycle:** Strictly execute within the 5-phase loop:
  $$\text{Observe} \longrightarrow \text{Plan} \longrightarrow \text{Act} \longrightarrow \text{Hook (PostToolUse)} \longrightarrow \text{Verify}$$
- **Automated Self-Healing:** When verification gates fail, pipe the compiler diagnostics, `stderr`, and stack traces directly into the next observation phase for automated self-repair.

## 2. Filesystem & Concurrency Isolation (Git Worktrees)
- **Protected Branch Guard:** NEVER write or commit code directly onto protected branches (`main`, `staging`).
- **Worktree Sandboxing:** Every parallel worker agent MUST operate strictly inside an isolated Git Worktree at `.worktrees/task-<id>` checked out to a dedicated feature branch `agent/<task-id>`.
- **Zero Collision Guarantee:** Parallel workers must never share working directories or race on file locks.

## 3. Workflow DAG Engineering & False-Edge Pruning
- **Declarative DAG Workflows:** Define multi-step or multi-agent tasks inside YAML specifications (`workflows/*.yaml`).
- **Eliminate False Edges:** Subtasks that do not exchange artifacts or data files must have artificial sequential dependencies pruned to enable parallel fan-out in concurrent execution waves.
- **Role Specialization:**
  - `Planner`: Formulates specifications, API contracts, and schema blueprints.
  - `Worker`: Implements code inside an isolated Git worktree using the self-healing loop.
  - `Verifier`: Pristine-context reviewer auditing raw git diffs.
  - `Synthesizer`: Integrates parallel branches, cleans temporary worktrees, and runs the final integration suite.
  - `Dream`: Consolidates episodic execution traces into Markdown memory.

## 4. Pristine-Context Verifier (Anti-Confirmation Bias)
- **Out-of-Band Audit:** An agent must never approve its own code within the same reasoning context thread.
- **Clean Diff Audit:** Route completed worker diffs to a Clean Verifier with a fresh context window containing only the original specification, the raw unified Git diff (`git diff`), and test runners.
- **Security & Regression Scans:** Actively block:
  - Critical insecure patterns (`eval()`, hardcoded secrets).
  - Concurrency deadlocks (e.g. SQLite `:memory:` under concurrent test runners - `FP-014`).
  - Unparameterized SQL or unvalidated endpoints.

## 5. 3-Tier Memory Architecture & Offline "Dreaming"
- **Tier 1 (Working Memory):** Current goal, unified diff, active compiler diagnostics.
- **Tier 2 (Episodic Memory):** Execution traces and event logs stored in `.logs/sessions/*.jsonl`.
- **Tier 3 (Semantic / Durable Memory):** Git-tracked, human-readable Markdown in `.memory/`.
  - Prior to planning any task, agents MUST read `.memory/architecture.md` and `.memory/failure-patterns.md`.
  - Document all verified edge cases, failure patterns, and architectural invariants.
  - After task completion, trigger the Dreaming Engine (`python -m src.cli memory dream`) to distill episodic traces into `.memory/*.md` and synchronize active rules into `GEMINI.md`.
