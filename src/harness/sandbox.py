"""Command and path execution sandbox for safety and security isolation."""
from __future__ import annotations
import os
from pathlib import Path
import re
from typing import List, Optional


class SandboxViolationError(Exception):
    """Raised when an operation violates path or command security boundaries."""
    pass


class CommandSandbox:
    """Enforces safety guardrails on file modifications and terminal commands."""

    BLOCKED_PATTERNS = [
        r"\brm\s+-(?:rf|fr|r)\s+/(?:\s|$)",
        r"\brm\s+-(?:rf|fr|r)\s+~(?:\s|$)",
        r"\bmkfs\b",
        r"\bdd\s+if=",
        r"\bshutdown\b",
        r"\breboot\b",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # Fork bomb
        r"\bgit\s+push\s+(?:--force|-f)\s+(?:origin\s+)?(?:main|master)\b",
        r"\bgit\s+branch\s+-(?:D|d)\s+(?:main|master)\b",
    ]

    def __init__(self, allowed_root: Optional[Path] = None):
        self.allowed_root = (allowed_root or Path.cwd()).resolve()

    def validate_command(self, command: str) -> None:
        """Validates that a shell command does not contain destructive operations."""
        cleaned = command.strip()
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                raise SandboxViolationError(
                    f"Command rejected by AgentGraph security sandbox: pattern '{pattern}' detected in '{command}'"
                )

    def validate_path(self, target_path: Path, worktree_root: Optional[Path] = None) -> Path:
        """
        Validates that a path is strictly confined within the allowed worktree or project root,
        preventing directory traversal attacks (e.g. ../../).
        """
        resolved = target_path.resolve()
        boundary = (worktree_root or self.allowed_root).resolve()

        try:
            resolved.relative_to(boundary)
        except ValueError:
            raise SandboxViolationError(
                f"Path traversal rejected! Path '{target_path}' resolves to '{resolved}' which is outside boundary '{boundary}'"
            )

        return resolved
