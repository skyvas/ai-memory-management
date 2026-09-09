"""PostToolUse hook triggers for formatting and linting after file edits."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, Optional


class HookRunner:
    """Executes automated hooks (e.g. formatters) following file writes or edits."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Loads hook configuration from .gemini/settings.json or fallback."""
        candidates = []
        if config_path:
            candidates.append(config_path)
        candidates.append(Path.cwd() / ".gemini" / "settings.json")
        candidates.append(Path.cwd() / ".claude" / "settings.json")

        for path in candidates:
            if path and path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass

        return {
            "hooks": {
                "postToolUse": {
                    "edit": "python -m black --quiet {filepath} 2>/dev/null || true",
                    "write": "python -m black --quiet {filepath} 2>/dev/null || true"
                }
            }
        }

    def trigger_post_tool_use(self, action: str, file_path: Path, cwd: Optional[Path] = None) -> bool:
        """
        Triggers the configured command for an action ('edit' or 'write').
        Replaces {filepath} with the target file path.
        """
        hooks = self.config.get("hooks", {}).get("postToolUse", {})
        cmd_template = hooks.get(action)
        if not cmd_template:
            return True

        cmd = cmd_template.replace("{filepath}", str(file_path))
        target_cwd = cwd or Path.cwd()

        try:
            subprocess.run(
                cmd,
                shell=True,
                cwd=str(target_cwd),
                capture_output=True,
                text=True,
                check=False
            )
            return True
        except Exception:
            return False
