"""Tests for Markdown memory manager and schemas."""
from pathlib import Path
import pytest

from src.memory.markdown_memory import MarkdownMemoryManager, FailurePattern, ADR


def test_add_and_read_failure_patterns(tmp_path: Path):
    manager = MarkdownMemoryManager(memory_dir=tmp_path)
    pattern = FailurePattern(
        id="FP-101",
        title="Flaky Port Binding in Concurrent Workers",
        date_str="2026-09-09",
        symptoms="Address already in use errors during pytest",
        root_cause="Hardcoded port numbers across parallel tests",
        rule="Always allocate dynamic ephemeral ports."
    )
    manager.add_failure_pattern(pattern)

    patterns = manager.read_failure_patterns()
    assert len(patterns) == 1
    assert patterns[0].id == "FP-101"
    assert "Always allocate dynamic ephemeral ports." in patterns[0].rule


def test_add_architecture_invariant(tmp_path: Path):
    manager = MarkdownMemoryManager(memory_dir=tmp_path)
    manager.add_invariant(
        category="Database",
        title="Transaction Isolation",
        rule="Use Serializable isolation for accounting writes.",
        task_ref="task-db-1"
    )

    content = manager.read_architecture()
    assert "## Database" in content
    assert "Transaction Isolation" in content
    assert "task-db-1" in content


def test_add_decision_record(tmp_path: Path):
    manager = MarkdownMemoryManager(memory_dir=tmp_path)
    adr = ADR(
        id="ADR-0005",
        title="Adoption of Native Gemini Models",
        status="Accepted",
        context="Migrating from legacy Claude to Google Gemini 2.5 Pro.",
        decision="Use Google Gen AI SDK for planning and verifiers.",
        consequences=["High throughput", "Native multimodal capability"]
    )
    saved_path = manager.add_decision_record(adr)
    assert saved_path.exists()
    content = saved_path.read_text()
    assert "# ADR-0005: Adoption of Native Gemini Models" in content
    assert "## Decision\nUse Google Gen AI SDK" in content
