"""Automated synchronization of distilled rules into GEMINI.md."""
from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional

from src.memory.markdown_memory import MarkdownMemoryManager


class GeminiUpdater:
    """Updates and synchronizes operational directives in GEMINI.md."""

    def __init__(self, gemini_file_path: Optional[Path] = None, memory_manager: Optional[MarkdownMemoryManager] = None):
        self.gemini_file = (gemini_file_path or Path.cwd() / "GEMINI.md").resolve()
        self.memory_manager = memory_manager or MarkdownMemoryManager()

    def sync(self) -> bool:
        """
        Synchronizes recent failure patterns and architecture rules from .memory/
        directly into the GEMINI.md directives file.
        """
        if not self.gemini_file.exists():
            return False

        patterns = self.memory_manager.read_failure_patterns()
        recent_rules = [f"- Avoid {p.id} ({p.title}): {p.rule}" for p in patterns[-5:]]
        rules_text = "\n".join(recent_rules) if recent_rules else "- No active failure pattern overrides."

        content = self.gemini_file.read_text(encoding="utf-8")
        section_header = "## 4. Active Distilled Rules (From Dreaming Engine)"

        new_section = (
            f"\n{section_header}\n"
            f"{rules_text}\n"
        )

        if section_header in content:
            # Replace existing section
            prefix = content.split(section_header)[0].rstrip()
            content = f"{prefix}\n{new_section}"
        else:
            # Append new section
            content = f"{content.rstrip()}\n{new_section}"

        self.gemini_file.write_text(content, encoding="utf-8")
        return True
