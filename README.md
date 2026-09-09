# AgentGraph: Autonomous Loop, Graph & Memory Engineering Harness

AgentGraph is a comprehensive multi-agent orchestration harness designed to transition software engineering from fragile, interactive chat prompts into deterministic, self-healing autonomous loops, directed acyclic dependency graphs (DAGs), and offline memory consolidation ("dreaming"). It pairs dynamic filesystem isolation via native Git Worktrees with binary compiler verification gates, clean-context reviewer agents, and biologically inspired semantic distillation.

All persistent agent memories, failure patterns, and architectural invariants are stored exclusively in human-readable, version-controlled Markdown (`.md`) files, allowing engineers to inspect, edit, and audit agent learnings directly in Git.

---

## 📑 Table of Contents

- [Architectural Paradigm Shift](#-architectural-paradigm-shift)
- [Core Architectural Pillars](#️-core-architectural-pillars)
  - [1. Autonomous Execution Loops (The Heartbeat)](#1-autonomous-execution-loops-the-heartbeat)
  - [2. Deterministic Verification Gates (Binary Truth)](#2-deterministic-verification-gates-binary-truth)
  - [3. Graph Engineering & False-Edge Pruning](#3-graph-engineering--false-edge-pruning)
  - [4. Pristine-Context Verifiers (Anti-Confirmation Bias)](#4-pristine-context-verifiers-anti-confirmation-bias)
  - [5. Native Git Worktree Isolation](#5-native-git-worktree-isolation)
  - [6. Memory Tiers & "Dreaming" (Offline Consolidation)](#6-memory-tiers--dreaming-offline-consolidation)
- [Markdown Memory Specification (.memory/*.md)](#-markdown-memory-specification-memorymd)
  - [Memory Directory Structure](#memory-directory-structure)
  - [Schema: Architecture & Invariants (architecture.md)](#schema-architecture--invariants-architecturemd)
  - [Schema: Failure Patterns & Anti-Patterns (failure-patterns.md)](#schema-failure-patterns--anti-patterns-failure-patternsmd)
  - [Schema: Decision Records (decisions/ADR-*.md)](#schema-decision-records-decisionsadr-md)
- [System Topology & Data Flow](#-system-topology--data-flow)
- [Project Management & Operating Model](#-project-management--operating-model)
  - [Role Boundaries: Autonomous Fleet vs. Human Supervisor](#role-boundaries-autonomous-fleet-vs-human-supervisor)
  - [Branching, Promotion & Merge Lifecycle](#branching-promotion--merge-lifecycle)
- [Tech Stack](#️-tech-stack)
- [Repository Layout](#-repository-layout)
- [Prerequisites & Environment Setup](#-prerequisites--environment-setup)
- [Quickstart Guide](#-quickstart-guide)
- [Configuration Contracts](#-configuration-contracts)
  - [Agent Operational Contract: GEMINI.md](#agent-operational-contract-geminimd)
  - [Tool Hooks: .gemini/settings.json](#tool-hooks-geminisettingsjson)
  - [Environment Variables: .env](#environment-variables-env)
- [Workflow Specification (DAG YAML Schema)](#-workflow-specification-dag-yaml-schema)
- [CLI Reference & Operations](#-cli-reference--operations)
  - [1. Running Multi-Agent Workflow Graphs](#1-running-multi-agent-workflow-graphs)
  - [2. Running Targeted Autonomous Loops](#2-running-targeted-autonomous-loops)
  - [3. Executing the Dreaming Memory Consolidation](#3-executing-the-dreaming-memory-consolidation)
  - [4. Managing Isolated Git Worktrees](#4-managing-isolated-git-worktrees)
- [Reliability, Quotas & Safety Controls](#-reliability-quotas--safety-controls)
- [Contributing & Development](#-contributing--development)
- [License](#-license)

---

## 💡 Architectural Paradigm Shift

Traditional AI coding workflows treat large language models as interactive conversational partners. While effective for simple snippets, this conversational model fails on complex software systems due to context sprawl, attention degradation, sycophantic validation, and subjective completion claims.

AgentGraph replaces conversational prompt tuning with an autonomous operational harness:

| Dimension | Legacy AI Coding (Chat / Prompting) | AgentGraph (Loops, Graphs & Dreaming) |
| :--- | :--- | :--- |
| **Control Model** | Human manually steers every prompt turn | Autonomous loops running against strict terminal goals |
| **Completion Criteria** | Subjective LLM assertion ("I fixed the code") | Deterministic exit code 0 from compilers and test runners |
| **Task Concurrency** | Single-threaded, sequential user prompts | Multi-agent DAG with false edges pruned for parallel fan-out |
| **Quality Review** | Agent critiques its own work in the same thread | Independent out-of-band verifier with zero prior context |
| **Workspace Model** | Shared local directory (prone to race conditions) | Isolated native Git Worktrees per concurrent task |
| **Memory Lifecycle** | Sliding-window context truncation (loses facts) | Multi-tier memory with offline Markdown consolidation |
| **Memory Storage** | Ephemeral context or opaque vector blobs | Version-controlled, human-readable Markdown (`.memory/*.md`) |

---

## 🏛️ Core Architectural Pillars

### 1. Autonomous Execution Loops (The Heartbeat)

Agents do not halt after a single file patch. They execute within an automated execution cycle:

$$\text{Observe} \longrightarrow \text{Plan} \longrightarrow \text{Act} \longrightarrow \text{Hook (PostToolUse)} \longrightarrow \text{Verify}$$

- **Observe**: Inspects current repository state, file contents, active diffs, and previous stderr output.
- **Plan**: Determines minimal atomic file modifications or terminal commands required.
- **Act**: Synthesizes patches natively or via Google Gemini models (`gemini-2.5-pro` / `gemini-2.5-flash`).
- **Hook**: Deterministically triggers code formatters and linters immediately after file writes.
- **Verify**: Runs compilation and unit test commands to check objective status. If checks fail, compiler diagnostics and stack traces feed directly into the next observation step for automated self-repair.

### 2. Deterministic Verification Gates (Binary Truth)

Subjective assertions (e.g., *"I have resolved the issue and verified the implementation"*) are treated as unverified claims. A node is considered complete **only** when external tooling returns process **exit code 0**.

- **Compilers & Type Checkers**: `mypy`, `pyright`, `tsc --noEmit`, `cargo check`, `go build`.
- **Test Suites**: `pytest`, `vitest`, `jest`, or Playwright end-to-end runners.
- **Linters & Formatters**: `ruff`, `black`, `flake8`, `biome`.

### 3. Graph Engineering & False-Edge Pruning

Large development epics are modeled as Directed Acyclic Graphs (DAGs) with strictly defined input and output schemas:

- **False-Edge Elimination**: Traditional engineering plans assume serial dependencies (e.g., waiting for backend services before scaffolding client hooks). If subtasks do not exchange data, these false sequential edges are pruned.
- **Parallel Fan-Out**: Independent worker nodes execute simultaneously across distinct agent runtimes in isolated Git worktrees, reducing total delivery duration from the sum of all tasks to the single longest path.

### 4. Pristine-Context Verifiers (Anti-Confirmation Bias)

When an agent is tasked with reviewing code it just wrote inside the same prompt thread, it suffers from severe confirmation bias and cognitive load.

- Passing worker outputs are routed to an independent **Verifier Node**.
- The Verifier runs in a fresh, unpolluted context window containing strictly the requirement specification, the raw unified git diff, and access to test suites.
- The Verifier inspects edge cases, regression risks, concurrency safety, and security vulnerabilities without rationalizing past mistakes.

### 5. Native Git Worktree Isolation

Running multiple autonomous agents concurrently within a single directory inevitably causes file collisions, git lock conflicts, and corrupted intermediate states.

- The harness provisions lightweight native Git Worktrees (`.worktrees/task-<id>`) checked out to isolated feature branches (`agent/<task-id>`) for each active worker.
- Agents operate on physical files on disk with zero container startup overhead while guaranteeing total branch and filesystem isolation.

### 6. Memory Tiers & "Dreaming" (Offline Consolidation)

Long-running agent workflows generate massive quantities of transient noise: verbose compiler errors, terminal outputs, and abandoned implementation attempts. Naive truncation causes amnesia, wiping away project conventions and architectural decisions.

AgentGraph implements a 3-tier memory model inspired by human sleep cycles:

```
┌────────────────────────────────────────────────────────┐
│               1. WORKING MEMORY (Context)              │
│  - Active goal, current file diff, immediate test log  │
│  - Scope: Current loop iteration (Minutes)             │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ (Token threshold reached or task complete)
┌────────────────────────────────────────────────────────┐
│               2. EPISODIC MEMORY (Logs)                │
│  - Raw bash histories, stack traces, patch iterations  │
│  - Scope: Ephemeral storage during session (Hours)     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ (Trigger: Offline Dreaming Phase)
┌────────────────────────────────────────────────────────┐
│               3. THE DREAMING CYCLE                    │
│  - Background subagent in pristine context             │
│  - Replays episodic trace & strips transient noise     │
│  - Distills lessons, codebase facts, & failure rules   │
│  - Writes updates directly to .memory/*.md & GEMINI.md │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│         4. SEMANTIC MEMORY (Human-Readable .md)        │
│  - Distilled repository architecture & rules in Git    │
│  - Formats: .memory/architecture.md, failure-patterns.md│
│  - Scope: Permanent cross-session storage              │
└────────────────────────────────────────────────────────┘
```

- **Episodic-to-Semantic Distillation**: A background engine re-evaluates the task log, extracting generalizable codebase knowledge into structured Markdown notes.
- **Self-Updating Instruction Files**: Distilled rules and lessons are automatically committed back to `GEMINI.md` and modular `.memory/*.md` files, upgrading instructions for subsequent runs.
- **Selective Forgetting**: Dead-end experiments and raw terminal logs are discarded from long-term memory, preventing token bloat.

---

## 📝 Markdown Memory Specification (`.memory/*.md`)

All permanent memories are maintained as plain, human-readable Markdown files stored in version control (`.memory/`). This ensures full developer transparency: engineers can read, git diff, edit, or delete any memory without needing database inspectors or binary deserializers.

### Memory Directory Structure

```text
.memory/
├── README.md                  # Guidelines on memory categorization & distillation rules
├── architecture.md            # System invariants, design patterns, cross-cutting rules
├── failure-patterns.md        # Identified anti-patterns, edge cases, and known regressions
├── conventions.md             # Code style conventions, naming rules, test fixtures
└── decisions/                 # Lightweight Architecture Decision Records (ADRs)
    ├── ADR-0001-example.md
    └── ADR-0002-pristine-context-gates.md
```

### Schema: Architecture & Invariants (`architecture.md`)

Maintains durable architectural facts discovered or verified during task runs:

```markdown
# Architecture Invariants & System Constants

*Last Updated by Agent Dreaming Engine: 2026-09-08 (Task: task-auth-v2)*

## Data Storage & Caching
- **Session Store:** Session tokens must be persisted using atomic Redis transactions (`MULTI/EXEC`). In-memory mock stores fail under concurrent test workers.
- **Transactions:** Wrap all balance adjustments in explicit transactions with `Serializable` isolation level.

## Inter-Service Communication
- **Internal APIs:** All internal service RPCs require an `x-correlation-id` header passed from the initial API Gateway request.
```

### Schema: Failure Patterns & Anti-Patterns (`failure-patterns.md`)

Logs recurring failure modes and how agents must proactively avoid them:

```markdown
# Known Failure Patterns & Regressions

This document is maintained by the Dreaming Engine to record resolved bugs and prevent regressions.

## FP-014: Worker Deadlocks on Shared SQLite Mocks
- **Date:** 2026-09-05
- **Symptoms:** Test suite hangs indefinitely when running concurrent test workers.
- **Root Cause:** In-memory SQLite (`:memory:`) cannot be safely accessed across concurrent worker processes without file backing.
- **Rule:** Always use dynamic per-worker temporary database files (`.tmp/test-${workerId}.db`) and clean up in test teardowns.

## FP-021: Missing Refresh Token Cookie Path Restriction
- **Date:** 2026-09-07
- **Symptoms:** Refresh tokens were transmitted to unrelated subpaths, failing security audit checks.
- **Rule:** Refresh token cookies must explicitly specify `Path=/api/v1/auth/refresh`, `HttpOnly=true`, and `SameSite=Strict`.
```

### Schema: Decision Records (`decisions/ADR-*.md`)

For major architectural choices made by Planner nodes, the system creates lightweight Markdown Architecture Decision Records:

```markdown
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
```

---

## 🌐 System Topology & Data Flow

```text
                                  [ User Request / Epic Goal ]
                                               │
                                               ▼
                               ┌───────────────────────────────┐
                               │    GRAPH ORCHESTRATOR (DAG)   │
                               │  - Parse Specifications       │
                               │  - Prune False Edges          │
                               │  - Schedule Task Allocations  │
                               └───────────────┬───────────────┘
                                               │
                       ┌───────────────────────┴───────────────────────┐
                       ▼                                               ▼
        ┌─────────────────────────────┐                 ┌─────────────────────────────┐
        │   WORKER NODE A (Backend)   │                 │   WORKER NODE B (Client)    │
        │   Worktree: .worktrees/wt-a │                 │   Worktree: .worktrees/wt-b │
        │   Loop: Observe-Act-Verify  │                 │   Loop: Observe-Act-Verify  │
        └──────────────┬──────────────┘                 └──────────────┬──────────────┘
                       │                                               │
                       └───────────────────────┬───────────────────────┘
                                               │ (Both Local Gates Pass exit 0)
                                               ▼
                               ┌───────────────────────────────┐
                               │  PRISTINE CONTEXT VERIFIER    │
                               │  - Zero Chat Memory Leakage   │
                               │  - Evaluates Raw Git Diff     │
                               │  - Security & Edge Case Gate  │
                               └───────────────┬───────────────┘
                                               │ (Approved)
                                               ▼
                               ┌───────────────────────────────┐
                               │       DREAMING ENGINE         │
                               │  - Distills Episodic Traces   │
                               │  - Synthesizes New Rules      │
                               │  - Commits .memory/*.md       │
                               │  - Syncs Operational GEMINI.md│
                               └───────────────┬───────────────┘
                                               │
                                               ▼
                               ┌───────────────────────────────┐
                               │     SYNTHESIZER & MERGE       │
                               │  - Rebase onto main           │
                               │  - Integration Tests (E2E)    │
                               │  - Cleanup Active Worktrees   │
                               └───────────────────────────────┘
```

---

## 👥 Project Management & Operating Model

High-autonomy software development requires clear structural boundaries between human oversight and automated agent execution.

### Role Boundaries: Autonomous Fleet vs. Human Supervisor

**The Autonomous Fleet:**
- Deconstructs feature goals into execution DAGs.
- Implements features, writes tests, runs compilation checks, and fixes syntax errors.
- Runs internal verification and cross-verifies patches in pristine reviewer contexts.
- Consolidates episodic operational knowledge into readable Markdown memory files via background dreaming cycles.

**The Human Supervisor:**
- Defines top-level business outcomes and constraints.
- Reviews and signs off on architectural RFCs generated by Planner nodes.
- Holds sole approval authority over final pull requests and production merges.
- Audits distilled Markdown learnings added to `.memory/*.md` and `GEMINI.md` to prevent policy drift.

### Branching, Promotion & Merge Lifecycle

```text
[main] ─────────────────────────────────────────────────────────────► [Release]
  │                                                               ▲
  ├─► [feature-epic]                                              │ (Human Approval)
  │     ├─► [agent/task-backend-wt1] ──┐                          │
  │     │   (Worktree Isolated)         │ (Verifier Pass)         │
  │     │                               ├─► [Synthesizer / E2E] ──┘
  │     └─► [agent/task-frontend-wt2] ──┘
  │         (Worktree Isolated)
```

1. **Epic Branch Creation**: A human or lead agent branches `feature/<epic-name>` from `main`.
2. **Worktree Allocation**: The DAG scheduler spawns short-lived branches (`agent/<task-id>`) inside isolated worktree directories.
3. **Loop Verification**: Workers iterate until static types and unit tests pass.
4. **Out-of-Band Audit**: A verifier subagent validates the aggregated diff.
5. **Dreaming & Consolidation**: Successful patterns and failure discoveries are distilled into `.memory/*.md` and synced into `GEMINI.md`.
6. **Merge Synthesis**: The Synthesizer merges task branches into the epic branch and runs end-to-end integration tests.
7. **Human Sign-Off**: The final pull request from the epic branch into `main` is presented to human maintainers.

---

## 🛠️ Tech Stack

| Category | Technologies | Purpose |
| :--- | :--- | :--- |
| **Language & Runtime** | Python 3.9+ (CPython / PyPy) | Core execution harness and orchestration engine |
| **Agent Foundation** | Native Google Gemini (`gemini-2.5-pro`, `gemini-2.5-flash`) | Reasoning, planning, coding, and review models |
| **CLI & Interface** | Click, Rich | Host environment interaction and terminal tables |
| **Verification & Compilers** | Pytest, Mypy, Ruff / Black | Binary exit code verification gates and code formatting |
| **Filesystem Isolation** | Native Git Worktrees (`git worktree add / remove / prune`) | High-speed, conflict-free parallel workspace isolation |
| **Memory Engine** | Background distillation writing directly to Markdown (`.memory/*.md` & `GEMINI.md`) | Offline episodic-to-semantic consolidation ("dreaming") |
| **Graph Processing** | Topological DAG engine with dynamic cycle detection | Workflow dependency scheduling and parallel fan-out |

---

## 📂 Repository Layout

```text
agent-graph-harness/
├── .gemini/
│   ├── settings.json              # Tool hooks (PostToolUse auto-formatters)
│   └── commands/                  # Custom agent operational commands
├── .memory/                       # Permanent human-readable semantic memory
│   ├── README.md                  # Memory system documentation & indexing rules
│   ├── architecture.md            # System invariants & architectural constants
│   ├── failure-patterns.md        # Documented anti-patterns, bugs & edge cases
│   ├── conventions.md             # Code style, test structures, naming rules
│   └── decisions/                 # Markdown Architecture Decision Records (ADRs)
│       └── ADR-0001-example.md
├── workflows/
│   ├── auth-service.yaml          # Sample workflow: Microservice auth overhaul
│   └── payment-migration.yaml     # Sample workflow: Multi-table schema migration
├── src/
│   ├── __init__.py
│   ├── cli.py                     # Main CLI entrypoint
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── dag_engine.py          # Topological sort & dependency execution
│   │   ├── optimizer.py           # False-edge pruner for parallelization
│   │   ├── parser.py              # YAML workflow validator
│   │   └── types.py               # Graph schema definitions
│   ├── harness/
│   │   ├── __init__.py
│   │   ├── git_worktree.py        # Native Git Worktree allocator & cleaner
│   │   ├── hooks.py               # PostToolUse formatter triggers
│   │   └── sandbox.py             # Path traversal and command safeguards
│   ├── loop/
│   │   ├── __init__.py
│   │   ├── agent_loop.py          # Observe-Plan-Act-Verify heartbeat
│   │   ├── verifier_gate.py       # Compilers, linters & test execution
│   │   └── token_budget.py        # Token consumption monitor
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── dreaming_engine.py     # Offline episodic-to-semantic compressor
│   │   ├── markdown_memory.py     # Parser, updater, and validator for .memory/*.md
│   │   ├── gemini_updater.py      # Automated GEMINI.md synchronization
│   │   └── context_pruner.py      # Active scratchpad garbage collector
│   └── verifier/
│       ├── __init__.py
│       └── clean_verifier.py      # Out-of-band fresh-context inspector
├── tests/
│   ├── __init__.py
│   ├── test_dag_engine.py
│   ├── test_git_worktree.py
│   ├── test_agent_loop.py
│   ├── test_markdown_memory.py
│   └── test_dreaming_engine.py
├── GEMINI.md                      # Primary agent system prompt & active rules
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## 📋 Prerequisites & Environment Setup

Ensure the host system meets these operational requirements:

- **Python**: v3.9 or higher
- **Git**: v2.30.0 or higher (with native `git worktree` support)
- **Google Gemini API Key** *(Optional)*: Set `GEMINI_API_KEY` for live model inference (offline/deterministic mode runs out of the box without any key).

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/your-org/agent-graph-harness.git
cd agent-graph-harness
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` to supply optional credentials and operational limits:

```ini
GEMINI_API_KEY=AIzaSy...
DEFAULT_MODEL=gemini-2.5-pro
FAST_MODEL=gemini-2.5-flash

# Loop & Operational Thresholds
MAX_LOOP_ITERATIONS=15
TOKEN_ALERT_THRESHOLD=80000
CONCURRENCY_LIMIT=4
WORKTREE_BASE_DIR=.worktrees
MEMORY_DIR=.memory
```

### 3. Verify Local Tooling & Run Tests

```bash
pytest tests/ -v
```

---

## ⚙️ Configuration Contracts

### Agent Operational Contract: `GEMINI.md`

The `GEMINI.md` file at the root of the repository serves as the strict deterministic contract governing all running agents:

```markdown
# Repository Directives for Autonomous Agents (Gemini)

## 1. Operating Axioms
- NEVER announce completion without a verified exit code 0 from testing tools.
- Never write code directly on protected branches (`main`, `staging`). Work strictly inside assigned Git Worktrees.
- Run tests after every substantive file change.

## 2. Deterministic Verification Gates
- Unit & Integration Testing: `pytest <target-path> -v`
- Process Exit Code: Process exit code must be strictly `0`.

## 3. Memory & Consolidation Directives
- Read architectural constants from `.memory/architecture.md` prior to planning.
- Document any verified edge-case fixes or failure patterns into `.memory/failure-patterns.md`.
- Keep intermediate edits clean; rely on PostToolUse formatters rather than fixing whitespace manually.
```

### Tool Hooks: `.gemini/settings.json`

Configure `.gemini/settings.json` so every code modification automatically triggers formatting before verification runs:

```json
{
  "hooks": {
    "postToolUse": {
      "edit": "python -m black --quiet {filepath} 2>/dev/null || true",
      "write": "python -m black --quiet {filepath} 2>/dev/null || true"
    }
  }
}
```

### Environment Variables: `.env`

Key operational parameters for tuning agent concurrency, context limits, and memory storage:

```ini
# Primary Model Routing (Google Gemini)
GEMINI_API_KEY=AIzaSy...
DEFAULT_MODEL=gemini-2.5-pro
FAST_MODEL=gemini-2.5-flash

# Concurrency & Worktree Controls
CONCURRENCY_LIMIT=4
WORKTREE_BASE_DIR=.worktrees
CLEANUP_ON_EXIT=true

# Loop Limits & Memory Controls
MAX_LOOP_ITERATIONS=15
TOKEN_ALERT_THRESHOLD=80000
DREAMING_TRIGGER_INTERVAL=5
MEMORY_DIR=.memory
```

---

## 📐 Workflow Specification (DAG YAML Schema)

Workflows coordinate complex multi-agent objectives via structured YAML. The parser prunes false edges, groups independent nodes for parallel execution, routes passing work to the verifier, and triggers dreaming cycles:

```yaml
version: "1.0"
name: "Production Auth & Session Overhaul"

nodes:
  # ----------------------------------------------------------------
  # 1. SPECIFICATION & CONTRACT DESIGN
  # ----------------------------------------------------------------
  - id: spec-planner
    type: planner
    prompt: |
      Design an RFC and interface definitions for JWT access and
      refresh token authentication. Define database schema contracts.
    outputs:
      - "specs/auth-rfc.md"
      - "schema/auth.json"
    verification:
      command: "python -c 'print(\"Spec contract validated\")'"

  # ----------------------------------------------------------------
  # 2. PARALLEL WORKERS (False edges pruned, fanned out concurrently)
  # ----------------------------------------------------------------
  - id: backend-worker
    type: worker
    inputs: ["specs/auth-rfc.md", "schema/auth.json"]
    worktree: true
    prompt: |
      Implement AuthController, SessionService, and token rotation routines.
      Ensure full test coverage.
    verification:
      command: "pytest tests/ -v"

  - id: frontend-worker
    type: worker
    inputs: ["specs/auth-rfc.md"]
    worktree: true
    prompt: |
      Implement session renewal hooks and client interceptors
      for 401 re-authentication.
    verification:
      command: "pytest tests/ -v"

  # ----------------------------------------------------------------
  # 3. PRISTINE CONTEXT VERIFICATION GATE
  # ----------------------------------------------------------------
  - id: security-verifier
    type: verifier
    freshContext: true
    inputs: ["backend-worker", "frontend-worker"]
    prompt: |
      Audit combined worktree diffs for security weaknesses:
      - Constant-time verification on token signatures
      - Secure, HttpOnly cookie flags on refresh tokens
      - Replay attacks and concurrency race conditions
    gate: "blocking"

  # ----------------------------------------------------------------
  # 4. MEMORY CONSOLIDATION ("DREAMING")
  # ----------------------------------------------------------------
  - id: consolidation-phase
    type: dream
    inputs: ["security-verifier"]
    target: ".memory/architecture.md"
    prompt: |
      Extract architectural patterns and test setup nuances discovered during
      backend and client implementation. Append verified rules to .memory/architecture.md
      and synchronize operational rules with GEMINI.md.

  # ----------------------------------------------------------------
  # 5. INTEGRATION & SYNTHESIS
  # ----------------------------------------------------------------
  - id: merge-synthesizer
    type: synthesizer
    inputs: ["consolidation-phase"]
    prompt: |
      Merge worktree branches into the staging epic branch and execute
      full system smoke and integration suites.
    verification:
      command: "pytest tests/ -v"
```

---

## 💻 CLI Reference & Operations

### 1. Running Multi-Agent Workflow Graphs

Execute a multi-stage DAG with dynamic fan-out and false-edge elimination:

```bash
# Execute standard workflow
python -m src.cli run-graph workflows/auth-service.yaml

# Execute with debug trace and custom concurrency
python -m src.cli run-graph workflows/auth-service.yaml --concurrency=6 --verbose

# Run simulation dry-run without modifying filesystem
python -m src.cli run-graph workflows/auth-service.yaml --dry-run
```

### 2. Running Targeted Autonomous Loops

Launch a standalone self-healing loop against an isolated objective:

```bash
python -m src.cli run-loop \
  --goal "Fix race condition in SessionStore token revocation" \
  --verify-cmd "pytest tests/test_agent_loop.py" \
  --max-retries 10 \
  --isolated-worktree
```

### 3. Executing the Dreaming Memory Consolidation

Manually trigger an episodic trace distillation pass across recent session logs to update Markdown memory:

```bash
python -m src.cli dream \
  --trace-dir .logs/sessions/ \
  --memory-dir .memory \
  --sync-gemini \
  --prune-transient
```

### 4. Managing Isolated Git Worktrees

Inspect, audit, or clean active agent worktrees:

```bash
# List all active agent workspaces
python -m src.cli worktrees:list

# Prune inactive worktrees and orphaned agent branches
python -m src.cli worktrees:clean --force
```

---

## 🛡️ Reliability, Quotas & Safety Controls

High-autonomy execution requires hard programmatic constraints to prevent runaways, runaway cloud costs, and filesystem corruption:

- **Context Management & Compaction**: Working context is continuously monitored. If token usage crosses 80,000 tokens (`TOKEN_ALERT_THRESHOLD`), the context manager triggers intermediate compaction, replacing raw shell outputs with concise structured summaries.
- **Iteration Quotas**: Every worker loop enforces a strict iteration threshold (`MAX_LOOP_ITERATIONS=15`). If objective tests do not pass within this quota, execution halts, state is persisted, and human intervention is flagged.
- **Execution Boundary Sandbox**: Shell execution tools are scoped strictly to the assigned `.worktrees/<task-id>` path. Destructive global commands (`rm -rf /`, `mkfs`, raw operations touching `.git` root) are intercepted and rejected.
- **Protected Branch Locking**: Agents cannot push or merge directly to `main` or production branches. Merging requires synthesis passing and final human supervisor review.

---

## 🤝 Contributing & Development

We welcome contributions to AgentGraph! To get started:

1. Fork the repository and create your feature branch:
   ```bash
   git checkout -b feature/dynamic-dag-pruning
   ```
2. Run test suites and format checks:
   ```bash
   pytest tests/ -v
   ```
3. Submit a Pull Request detailing the changes, benchmark metrics, and test coverage.

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
