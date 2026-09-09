"""Token consumption monitor and alert thresholds for autonomous loops."""
from __future__ import annotations
from dataclasses import dataclass, field
import os
from typing import List, Optional


@dataclass
class TokenUsage:
    iteration: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class TokenBudgetMonitor:
    """Monitors token usage across loop iterations and raises alerts at threshold."""

    def __init__(self, alert_threshold: Optional[int] = None):
        self.alert_threshold = alert_threshold or int(os.environ.get("TOKEN_ALERT_THRESHOLD", 80000))
        self.history: List[TokenUsage] = []
        self._cumulative_tokens: int = 0

    @property
    def cumulative_tokens(self) -> int:
        return self._cumulative_tokens

    def record_usage(self, prompt_tokens: int, completion_tokens: int, iteration: int = 1) -> TokenUsage:
        """Records token usage for an iteration."""
        total = prompt_tokens + completion_tokens
        self._cumulative_tokens += total
        usage = TokenUsage(
            iteration=iteration,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total
        )
        self.history.append(usage)
        return usage

    def is_threshold_exceeded(self) -> bool:
        """Checks if current cumulative token usage exceeds the alert threshold."""
        return self._cumulative_tokens >= self.alert_threshold

    def get_compaction_recommendation(self) -> Optional[str]:
        """Returns compaction directive if threshold is exceeded."""
        if self.is_threshold_exceeded():
            return (
                f"ALERT: Cumulative token consumption ({self._cumulative_tokens:,}) "
                f"exceeds alert threshold ({self.alert_threshold:,}). "
                "Immediate context compaction recommended: prune transient terminal logs and bash histories."
            )
        return None
