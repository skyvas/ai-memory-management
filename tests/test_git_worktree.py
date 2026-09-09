"""Tests for native Git Worktree lifecycle and isolation."""
import subprocess
import pytest
from pathlib import Path

from src.harness.git_worktree import GitWorktreeManager


def test_worktree_path_sanitization(tmp_path: Path):
    manager = GitWorktreeManager(repo_root=tmp_path)
    wt_path = manager.get_task_worktree_path("task/feature:1")
    assert "task_feature_1" in str(wt_path)


def test_worktree_lifecycle_in_git_repo(tmp_path: Path):
    # Initialize a temporary git repository for testing
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "agent@agentgraph.local"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "config", "user.name", "AgentGraph Test"], cwd=str(tmp_path), check=True)

    # Initial commit
    (tmp_path / "README.md").write_text("# Initial Commit\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(tmp_path), check=True)

    manager = GitWorktreeManager(repo_root=tmp_path, worktree_base_dir=".test_worktrees")

    # 1. Create worktree
    wt_path = manager.create_worktree("auth-task-1")
    assert wt_path.exists()
    assert (wt_path / "README.md").exists()

    # 2. List worktrees
    worktrees = manager.list_worktrees()
    paths = [w.path for w in worktrees]
    assert any("task-auth-task-1" in p for p in paths)

    # 3. Clean all task worktrees
    cleaned = manager.clean_all_task_worktrees(force=True)
    assert cleaned >= 1
    assert not wt_path.exists()
