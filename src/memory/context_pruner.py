"""Active scratchpad garbage collector and transient noise pruner."""
from __future__ import annotations
import re
from typing import Any, Dict, List


class ContextPruner:
    """Discards transient terminal noise and dead-ends while preserving semantic facts."""

    NOISE_PATTERNS = [
        r"npm\s+(?:warn|notice)\b[^\n]*\n?",
        r"Traceback \(most recent call last\):[\s\S]*?(?=\n\w+Error:)",
        r"(?:[\w\.-]+/[\w\.-]+)+\s+\d+%\s+\[=+\][^\n]*\n?",
        r"\x1b\[[0-9;]*[a-zA-Z]",  # ANSI escape codes
    ]

    @classmethod
    def prune_text(cls, text: str) -> str:
        """Removes verbose terminal noise and ANSI codes from execution logs."""
        cleaned = text
        for pat in cls.NOISE_PATTERNS:
            cleaned = re.sub(pat, "", cleaned, flags=re.MULTILINE)
        # Collapse excessive newlines
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @classmethod
    def compact_session_trace(cls, log_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filters out low-signal intermediate steps, retaining only:
        - Initial task goals
        - File patch diffs
        - Verified exit code events
        """
        compacted = []
        for event in log_events:
            ev_type = event.get("type", "")
            if ev_type in {"goal", "diff", "verification", "invariant", "error_resolution"}:
                event_copy = dict(event)
                if "output" in event_copy and isinstance(event_copy["output"], str):
                    event_copy["output"] = cls.prune_text(event_copy["output"])[:1000]
                compacted.append(event_copy)
        return compacted
