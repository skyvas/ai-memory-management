"""Unit tests for Git-native .agents/ Multi-Agent Development & Memory Engine."""
import pytest
from pathlib import Path
import tempfile
import shutil
import json

from src.dev_engine.memory_manager import (
    MemoryManager,
    MemoryRecord,
    MemoryType,
    MemoryScope,
    MemoryStatus,
)
from src.dev_engine.dev_agents import ResearchAgent, CodingAgent, PlanningAgent
from src.dev_engine.dream_consolidation import DreamOrchestrator


@pytest.fixture
def temp_agents_dir():
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / ".agents"
    yield agents_path
    if agents_path.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_manager_file_structure(temp_agents_dir):
    mm = MemoryManager(base_dir=temp_agents_dir)
    assert temp_agents_dir.exists()
    assert (temp_agents_dir / "semantic").exists()
    assert (temp_agents_dir / "episodic").exists()
    assert (temp_agents_dir / "working").exists()
    assert (temp_agents_dir / "versions.json").exists()
    assert (temp_agents_dir / "project_state.json").exists()

    versions = mm.get_versions()
    assert len(versions) == 1
    assert versions[0].version_number == 1

    # 1. Test remember episodic item -> appends to episodic_log.jsonl
    rec = MemoryRecord(
        content="Test finding: raw password column exposed",
        type=MemoryType.EPISODIC,
        importance=0.8,
    )
    saved = mm.remember(rec)
    assert saved is not None
    assert saved.id == rec.id

    episodic_file = temp_agents_dir / "episodic" / "episodic_log.jsonl"
    assert episodic_file.exists()
    lines = episodic_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["content"] == rec.content

    # 2. Low importance should be filtered out by admission policy
    low_rec = MemoryRecord(
        content="Trivial log",
        type=MemoryType.WORKING,
        importance=0.1,
    )
    assert mm.remember(low_rec) is None

    # 3. Test remember semantic item -> writes .md file in semantic/
    sem_rec = MemoryRecord(
        content="Verified Rule: PCI-DSS 3.4 requires PAN masking.",
        type=MemoryType.SEMANTIC,
        importance=0.9,
    )
    mm.remember(sem_rec)
    sem_file = temp_agents_dir / "semantic" / f"{sem_rec.id}.md"
    assert sem_file.exists()
    sem_text = sem_file.read_text(encoding="utf-8")
    assert "type: semantic" in sem_text
    assert "PCI-DSS 3.4 requires PAN masking" in sem_text

    # 4. Recall
    recalled = mm.recall(query="password")
    assert len(recalled) == 1
    assert "password" in recalled[0].content

    recalled_sem = mm.recall(mem_type=MemoryType.SEMANTIC)
    assert len(recalled_sem) == 1
    assert "PCI-DSS" in recalled_sem[0].content


def test_dev_agents_and_dream_cycle_in_agents_dir(temp_agents_dir):
    mm = MemoryManager(base_dir=temp_agents_dir)

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

    # Check semantic memory promoted to Markdown files
    semantics = mm.recall(mem_type=MemoryType.SEMANTIC)
    assert len(semantics) >= 1

    semantic_files = list((temp_agents_dir / "semantic").glob("*.md"))
    assert len(semantic_files) >= 1
    for sf in semantic_files:
        content = sf.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "type: semantic" in content

    # Test Reset
    mm.clear()
    assert len(mm.recall(limit=100)) == 0
    assert mm.get_versions()[0].version_number == 1
    assert len(list((temp_agents_dir / "semantic").glob("*.md"))) == 0
