"""Tests for episodic trace distillation and dreaming consolidation."""
import json
from pathlib import Path
import pytest

from src.memory.dreaming_engine import DreamingEngine
from src.memory.gemini_updater import GeminiUpdater
from src.memory.markdown_memory import MarkdownMemoryManager


def test_dreaming_consolidation_and_gemini_sync(tmp_path: Path):
    memory_dir = tmp_path / ".memory"
    trace_dir = tmp_path / "traces"
    trace_dir.mkdir(parents=True)
    gemini_file = tmp_path / "GEMINI.md"
    gemini_file.write_text("# Directives\n\n## 1. Operating Axioms\n- Exit code 0 required.\n")

    # Create dummy episodic trace file
    trace_data = [
        {"type": "goal", "output": "Implement auth middleware"},
        {
            "type": "error_resolution",
            "title": "Unauthenticated CORS rejection",
            "symptoms": "Browser blocked OPTIONS preflight",
            "root_cause": "Missing Access-Control-Allow-Credentials header",
            "rule": "Always explicitly allow credentials when using cookies."
        },
        {
            "type": "invariant",
            "category": "Security",
            "title": "Cookie Flags",
            "rule": "Cookies must specify SameSite=Strict and HttpOnly=True."
        }
    ]
    (trace_dir / "session_auth_1.json").write_text(json.dumps(trace_data))

    mem_manager = MarkdownMemoryManager(memory_dir=memory_dir)
    engine = DreamingEngine(memory_manager=mem_manager, trace_dir=trace_dir)
    engine.gemini_updater = GeminiUpdater(gemini_file_path=gemini_file, memory_manager=mem_manager)

    res = engine.run_dreaming_cycle(sync_gemini=True, prune_transient=True)

    assert res.traces_processed == 1
    assert res.new_failure_patterns == 1
    assert res.new_invariants == 1
    assert res.gemini_synced is True

    # Verify memory files updated
    patterns = mem_manager.read_failure_patterns()
    assert any("Unauthenticated CORS rejection" in p.title for p in patterns)

    # Verify GEMINI.md was updated with distilled rule
    gemini_content = gemini_file.read_text()
    assert "Active Distilled Rules" in gemini_content
    assert "Always explicitly allow credentials" in gemini_content
