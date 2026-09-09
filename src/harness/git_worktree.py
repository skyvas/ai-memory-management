"""Native Git Worktree management for dynamic agent isolation."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional


@dataclass
class WorktreeInfo:
    path: str
    head: str
    branch: Optional[str] = None
    is_bare: bool = False
    is_detached: bool = False


class GitWorktreeError(Exception):
    """Raised when git worktree operations fail."""
    pass


class GitWorktreeManager:
    """Manages creation, inspection, and deletion of native Git Worktrees."""

    def __init__(self, repo_root: Optional[Path] = None, worktree_base_dir: str = ".worktrees"):
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.worktree_base = self.repo_root / worktree_base_dir
        self.worktree_base.mkdir(parents=True, exist_ok=True)

    def _run_git(self, args: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
        """Runs a git command safely."""
        target_cwd = cwd or self.repo_root
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(target_cwd),
                capture_output=True,
                text=True,
                check=False
            )
            return res
        except Exception as e:
            raise GitWorktreeError(f"Failed to execute git command '{' '.join(cmd)}': {e}") from e

    def get_task_worktree_path(self, task_id: str) -> Path:
        """Returns the filesystem path for a task worktree."""
        sanitized_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        return self.worktree_base / f"task-{sanitized_id}"

    def create_worktree(
        self,
        task_id: str,
        branch_name: Optional[str] = None,
        base_commit: str = "HEAD"
    ) -> Path:
        """
        Creates an isolated native Git Worktree checked out to a task branch.
        """
        wt_path = self.get_task_worktree_path(task_id)
        sanitized_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        branch = branch_name or f"agent/{sanitized_id}"

        # If worktree already exists, remove it first
        if wt_path.exists():
            self.remove_worktree(task_id, force=True, delete_branch=False)

        # Check if branch exists
        branch_check = self._run_git(["rev-parse", "--verify", branch])
        if branch_check.returncode == 0:
            # Branch already exists; add worktree pointing to it
            res = self._run_git(["worktree", "add", str(wt_path), branch])
        else:
            # Create new branch from base_commit
            res = self._run_git(["worktree", "add", "-b", branch, str(wt_path), base_commit])

        if res.returncode != 0:
            raise GitWorktreeError(
                f"Failed to create git worktree at {wt_path}: {res.stderr.strip() or res.stdout.strip()}"
            )

        return wt_path

    def remove_worktree(self, task_id: str, force: bool = True, delete_branch: bool = True) -> bool:
        """Removes an active task worktree and optionally deletes its isolated branch."""
        wt_path = self.get_task_worktree_path(task_id)
        sanitized_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        branch = f"agent/{sanitized_id}"

        success = True
        if wt_path.exists():
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(str(wt_path))
            res = self._run_git(args)
            if res.returncode != 0:
                # Fallback to direct directory removal if git worktree remove fails
                if wt_path.exists():
                    shutil.rmtree(wt_path, ignore_errors=True)
                self.prune_worktrees()

        if delete_branch:
            del_res = self._run_git(["branch", "-D" if force else "-d", branch])
            # Ignore returncode if branch doesn't exist

        self.prune_worktrees()
        return success

    def list_worktrees(self) -> List[WorktreeInfo]:
        """Parses native `git worktree list --porcelain` output."""
        res = self._run_git(["worktree", "list", "--porcelain"])
        if res.returncode != 0:
            raise GitWorktreeError(f"Failed to list git worktrees: {res.stderr}")

        worktrees: List[WorktreeInfo] = []
        lines = res.stdout.splitlines()
        current_wt: Optional[WorktreeInfo] = None

        for line in lines:
            line = line.strip()
            if not line:
                if current_wt:
                    worktrees.append(current_wt)
                    current_wt = None
                continue

            parts = line.split(" ", 1)
            key = parts[0]
            val = parts[1] if len(parts) > 1 else ""

            if key == "worktree":
                current_wt = WorktreeInfo(path=val, head="")
            elif current_wt and key == "HEAD":
                current_wt.head = val
            elif current_wt and key == "branch":
                current_wt.branch = val
            elif current_wt and key == "bare":
                current_wt.is_bare = True
            elif current_wt and key == "detached":
                current_wt.is_detached = True

        if current_wt:
            worktrees.append(current_wt)

        return worktrees

    def prune_worktrees(self) -> None:
        """Prunes stale git worktree administrative files."""
        self._run_git(["worktree", "prune"])

    def clean_all_task_worktrees(self, force: bool = True) -> int:
        """Removes all worktrees located in the worktree base directory."""
        wts = self.list_worktrees()
        count = 0
        base_str = str(self.worktree_base.resolve())

        for wt in wts:
            wt_path_resolved = Path(wt.path).resolve()
            if str(wt_path_resolved).startswith(base_str):
                args = ["worktree", "remove"]
                if force:
                    args.append("--force")
                args.append(str(wt_path_resolved))
                self._run_git(args)
                if wt_path_resolved.exists():
                    shutil.rmtree(wt_path_resolved, ignore_errors=True)
                count += 1

        self.prune_worktrees()
        return count
