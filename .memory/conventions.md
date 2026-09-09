# Code Style & Development Conventions

## Code Quality Standards
- Strict type hinting across all Python classes, function parameters, and return types.
- Format all files using standard formatting tools before committing.
- Do not bypass verification gates: processes must exit with code `0`.

## Testing Standards
- All test suites must execute cleanly via `pytest`.
- Test files must be isolated; never share mutable state across test functions.
- Use fixtures (`@pytest.fixture`) for temporary directory setup and mock object lifecycles.

## Worktree & Branch Naming
- Worktrees: `.worktrees/task-<id>`
- Agent Branches: `agent/<id>`
- Synthesizer Branches: `synth/<epic-id>`
