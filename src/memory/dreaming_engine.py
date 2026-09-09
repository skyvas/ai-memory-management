"""Offline episodic-to-semantic memory consolidation ("Dreaming Engine")."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.memory.context_pruner import ContextPruner
from src.memory.gemini_updater import GeminiUpdater
from src.memory.markdown_memory import FailurePattern, MarkdownMemoryManager


@dataclass
class DreamingResult:
    traces_processed: int
    new_invariants: int
    new_failure_patterns: int
    gemini_synced: bool
    summary: str


class DreamingEngine:
    """Consolidates episodic session traces into durable Markdown memory (.memory/*.md)."""

    def __init__(
        self,
        memory_manager: Optional[MarkdownMemoryManager] = None,
        trace_dir: Optional[Path] = None,
        llm_fn: Optional[Callable[[str], str]] = None
    ):
        self.memory_manager = memory_manager or MarkdownMemoryManager()
        self.trace_dir = (trace_dir or Path.cwd() / ".logs" / "sessions").resolve()
        self.gemini_updater = GeminiUpdater(memory_manager=self.memory_manager)
        self.llm_fn = llm_fn

    def distill_trace_data(self, events: List[Dict[str, Any]], session_id: str = "session-1") -> Dict[str, Any]:
        """
        Extracts reusable architectural invariants and failure patterns from a session trace.
        Can run with rule-based heuristics or Gemini LLM.
        """
        compacted = ContextPruner.compact_session_trace(events)
        today = date.today().isoformat()

        extracted_invariants = []
        extracted_patterns = []

        # Analyze errors resolved in the trace
        for event in compacted:
            if event.get("type") == "error_resolution":
                fp_id = f"FP-{len(self.memory_manager.read_failure_patterns()) + 101:03d}"
                pat = FailurePattern(
                    id=fp_id,
                    title=event.get("title", f"Resolved issue in {session_id}"),
                    date_str=today,
                    symptoms=event.get("symptoms", "Process exited with non-zero status"),
                    root_cause=event.get("root_cause", "Misconfiguration or concurrency contention"),
                    rule=event.get("rule", "Ensure resource isolation and explicit error handling.")
                )
                extracted_patterns.append(pat)

            elif event.get("type") == "invariant":
                extracted_invariants.append({
                    "category": event.get("category", "General"),
                    "title": event.get("title", "System Rule"),
                    "rule": event.get("rule", "")
                })

        return {
            "invariants": extracted_invariants,
            "patterns": extracted_patterns,
            "compacted_count": len(compacted)
        }

    def run_dreaming_cycle(
        self,
        sync_gemini: bool = True,
        prune_transient: bool = True
    ) -> DreamingResult:
        """Executes a full dreaming pass across session log files."""
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        trace_files = list(self.trace_dir.glob("*.json")) + list(self.trace_dir.glob("*.jsonl"))

        invariants_added = 0
        patterns_added = 0

        for t_file in trace_files:
            try:
                events: List[Dict[str, Any]] = []
                if t_file.suffix == ".jsonl":
                    for line in t_file.read_text(encoding="utf-8").splitlines():
                        if line.strip():
                            events.append(json.loads(line))
                else:
                    data = json.loads(t_file.read_text(encoding="utf-8"))
                    events = data if isinstance(data, list) else data.get("events", [])

                distilled = self.distill_trace_data(events, session_id=t_file.stem)

                for inv in distilled["invariants"]:
                    self.memory_manager.add_invariant(
                        category=inv["category"],
                        title=inv["title"],
                        rule=inv["rule"],
                        task_ref=t_file.stem
                    )
                    invariants_added += 1

                for pat in distilled["patterns"]:
                    self.memory_manager.add_failure_pattern(pat)
                    patterns_added += 1

                if prune_transient:
                    # Clean or remove processed episodic log
                    t_file.unlink(missing_ok=True)

            except Exception:
                continue

        synced = False
        if sync_gemini:
            synced = self.gemini_updater.sync()

        summary = (
            f"Dreaming Cycle Complete: Processed {len(trace_files)} trace(s), "
            f"added {invariants_added} invariant(s), {patterns_added} failure pattern(s). "
            f"GEMINI.md synced: {synced}."
        )

        return DreamingResult(
            traces_processed=len(trace_files),
            new_invariants=invariants_added,
            new_failure_patterns=patterns_added,
            gemini_synced=synced,
            summary=summary
        )
