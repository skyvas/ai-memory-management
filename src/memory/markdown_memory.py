"""Markdown memory specification manager (.memory/*.md)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import os
from pathlib import Path
import re
from typing import Dict, List, Optional


@dataclass
class FailurePattern:
    id: str
    title: str
    date_str: str
    symptoms: str
    root_cause: str
    rule: str

    def to_markdown(self) -> str:
        return (
            f"## {self.id}: {self.title}\n"
            f"- **Date:** {self.date_str}\n"
            f"- **Symptoms:** {self.symptoms}\n"
            f"- **Root Cause:** {self.root_cause}\n"
            f"- **Rule:** {self.rule}\n"
        )


@dataclass
class ArchitectureInvariant:
    category: str
    title: str
    rule: str


@dataclass
class ADR:
    id: str
    title: str
    status: str
    context: str
    decision: str
    consequences: List[str]

    def to_markdown(self) -> str:
        consequences_md = "\n".join(f"- {c}" for c in self.consequences)
        return (
            f"# {self.id}: {self.title}\n\n"
            f"## Status\n{self.status}\n\n"
            f"## Context\n{self.context}\n\n"
            f"## Decision\n{self.decision}\n\n"
            f"## Consequences\n{consequences_md}\n"
        )


class MarkdownMemoryManager:
    """Provides type-safe parsing, updating, and governance for .memory/*.md files."""

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = (memory_dir or Path(os.environ.get("MEMORY_DIR", ".memory"))).resolve()
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "decisions").mkdir(parents=True, exist_ok=True)

        self.arch_file = self.memory_dir / "architecture.md"
        self.failure_file = self.memory_dir / "failure-patterns.md"
        self.conventions_file = self.memory_dir / "conventions.md"

    def read_architecture(self) -> str:
        """Reads raw architecture.md markdown content."""
        if self.arch_file.exists():
            return self.arch_file.read_text(encoding="utf-8")
        return "# Architecture Invariants & System Constants\n"

    def add_invariant(self, category: str, title: str, rule: str, task_ref: str = "") -> None:
        """Appends or updates an architectural invariant."""
        content = self.read_architecture()
        today = date.today().isoformat()
        header = f"## {category}"

        new_entry = f"- **{title}:** {rule}\n"

        if header in content:
            # Append under existing category header
            parts = content.split(header, 1)
            content = parts[0] + header + "\n" + new_entry + parts[1].lstrip("\n")
        else:
            # Add new category section
            content = content.rstrip() + f"\n\n{header}\n{new_entry}"

        # Update or insert last updated line
        if "*Last Updated by Agent Dreaming Engine:" in content:
            content = re.sub(
                r"\*Last Updated by Agent Dreaming Engine:[^*]+\*",
                f"*Last Updated by Agent Dreaming Engine: {today} ({task_ref})*",
                content
            )
        elif task_ref:
            lines = content.splitlines()
            if lines and lines[0].startswith("# "):
                content = lines[0] + f"\n\n*Last Updated by Agent Dreaming Engine: {today} ({task_ref})*\n" + "\n".join(lines[1:])
            else:
                content = f"*Last Updated by Agent Dreaming Engine: {today} ({task_ref})*\n\n" + content

        self.arch_file.write_text(content, encoding="utf-8")

    def read_failure_patterns(self) -> List[FailurePattern]:
        """Parses failure-patterns.md into FailurePattern objects."""
        if not self.failure_file.exists():
            return []

        content = self.failure_file.read_text(encoding="utf-8")
        patterns: List[FailurePattern] = []

        # Regex to extract failure pattern sections
        pattern_regex = re.compile(
            r"^##\s+([A-Z0-9_-]+):\s*(.+?)\n"
            r"- \*\*Date:\*\*\s*(.+?)\n"
            r"- \*\*Symptoms:\*\*\s*(.+?)\n"
            r"- \*\*Root Cause:\*\*\s*(.+?)\n"
            r"- \*\*Rule:\*\*\s*(.+?)(?=\n##|\Z)",
            re.MULTILINE | re.DOTALL
        )

        for match in pattern_regex.finditer(content):
            fp_id = match.group(1).strip()
            title = match.group(2).strip()
            date_str = match.group(3).strip()
            symptoms = match.group(4).strip()
            root_cause = match.group(5).strip()
            rule = match.group(6).strip()
            patterns.append(
                FailurePattern(
                    id=fp_id,
                    title=title,
                    date_str=date_str,
                    symptoms=symptoms,
                    root_cause=root_cause,
                    rule=rule
                )
            )

        return patterns

    def add_failure_pattern(self, pattern: FailurePattern) -> None:
        """Appends a new failure pattern to failure-patterns.md."""
        existing = self.read_failure_patterns()
        # Check if ID already exists
        for idx, ex in enumerate(existing):
            if ex.id == pattern.id:
                existing[idx] = pattern
                self._write_failure_patterns(existing)
                return

        existing.append(pattern)
        self._write_failure_patterns(existing)

    def _write_failure_patterns(self, patterns: List[FailurePattern]) -> None:
        """Writes failure pattern objects to failure-patterns.md."""
        header = (
            "# Known Failure Patterns & Regressions\n\n"
            "This document is maintained by the Dreaming Engine to record resolved bugs and prevent regressions.\n\n"
        )
        body = "\n".join(p.to_markdown() for p in patterns)
        self.failure_file.write_text(header + body, encoding="utf-8")

    def add_decision_record(self, adr: ADR) -> Path:
        """Saves a new Architecture Decision Record in .memory/decisions/."""
        decisions_dir = self.memory_dir / "decisions"
        decisions_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{adr.id}-{adr.title.lower().replace(' ', '-')}.md"
        # Sanitize filename
        filename = "".join(c if c.isalnum() or c in "-_." else "_" for c in filename)
        file_path = decisions_dir / filename
        file_path.write_text(adr.to_markdown(), encoding="utf-8")
        return file_path
