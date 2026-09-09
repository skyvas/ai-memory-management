"""Unit tests for Multi-Agent Development & Self-Critique Engine."""
import pytest
from pathlib import Path
import tempfile
import os

from src.dev_engine.memory_manager import (
    MemoryManager,
    MemoryRecord,
    MemoryType,
    MemoryScope,
)
from src.dev_engine.dev_agents import ResearchAgent, CodingAgent, PlanningAgent
from src.dev_engine.dream_consolidation import DreamOrchestrator


@pytest.fixture
def temp_db():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_memory.db")
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_memory_manager_lifecycle(temp_db):
    mm = MemoryManager(db_path=temp_db)
    assert len(mm.get_versions()) == 1

    # Remember episodic item
    rec = MemoryRecord(
        content="Test finding: raw password column exposed",
        type=MemoryType.EPISODIC,
        importance=0.8,
    )
    saved = mm.remember(rec)
    assert saved is not None
    assert saved.id == rec.id

    # Low importance should be filtered out by admission pipeline
    low_rec = MemoryRecord(
        content="Trivial log",
        type=MemoryType.WORKING,
        importance=0.1,
    )
    assert mm.remember(low_rec) is None

    # Recall
    recalled = mm.recall(query="password")
    assert len(recalled) == 1
    assert "password" in recalled[0].content


def test_dev_agents_and_dream_cycle(temp_db):
    mm = MemoryManager(db_path=temp_db)

    # Waking Mode
    researcher = ResearchAgent(mm)
    coder = CodingAgent(mm)
    planner = PlanningAgent(mm)

    res_res = researcher.run("PII research", {})
    assert res_res["status"] == "completed"

    code_res = coder.run("Benchmark scan", {
        "sql_sample": "samples/vulnerable_store.sql",
        "mongo_sample": "samples/mongo_users.json"
    })
    assert code_res["status"] == "completed"

    plan_res = planner.run("Milestone", {})
    assert plan_res["status"] == "completed"

    # Dreaming Mode
    orchestrator = DreamOrchestrator(mm)
    dream_res = orchestrator.run_dream_cycle()

    assert dream_res["status"] == "completed"
    assert dream_res["approved_proposals_count"] >= 1
    assert dream_res["new_version"]["version_number"] == 2

    # Check semantic memory promoted
    semantics = mm.recall(mem_type=MemoryType.SEMANTIC)
    assert len(semantics) >= 1

    # Test Reset
    mm.clear()
    assert len(mm.recall(limit=100)) == 0
    assert mm.get_versions()[0].version_number == 1
