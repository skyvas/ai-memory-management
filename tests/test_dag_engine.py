"""Tests for workflow DAG parsing, false-edge pruning, cycle detection, and execution."""
import pytest
from pathlib import Path

from src.graph.parser import WorkflowParser, WorkflowParserError
from src.graph.optimizer import DAGOptimizer, GraphOptimizationError
from src.graph.dag_engine import DAGEngine
from src.graph.types import DAGNode, NodeType, GateMode, VerificationSpec, WorkflowSpec


def test_parse_valid_workflow(tmp_path: Path):
    yaml_content = """
    version: "1.0"
    name: "Test Flow"
    nodes:
      - id: planner-node
        type: planner
        prompt: "Create spec"
        outputs: ["spec.md"]
      - id: worker-node
        type: worker
        inputs: ["spec.md"]
        prompt: "Implement code"
        verification:
          command: "echo 0"
    """
    wf_file = tmp_path / "test_flow.yaml"
    wf_file.write_text(yaml_content)

    spec = WorkflowParser.parse_file(wf_file)
    assert spec.name == "Test Flow"
    assert len(spec.nodes) == 2
    assert spec.nodes[0].type == NodeType.PLANNER
    assert spec.nodes[1].type == NodeType.WORKER
    assert spec.nodes[1].inputs == ["spec.md"]


def test_parse_duplicate_node_ids_raises_error():
    wf_dict = {
        "name": "Invalid Flow",
        "nodes": [
            {"id": "node-1", "type": "worker", "prompt": "task 1"},
            {"id": "node-1", "type": "worker", "prompt": "task 2"},
        ]
    }
    with pytest.raises(WorkflowParserError, match="Duplicate node ID"):
        WorkflowParser.parse_dict(wf_dict)


def test_false_edge_pruning_and_parallel_waves():
    """
    Verify false-edge pruning:
    If Worker A and Worker B both depend on spec.md from Planner,
    but have no dependency on each other, they MUST run in parallel (same wave).
    """
    planner = DAGNode(id="planner", type=NodeType.PLANNER, prompt="Spec", outputs=["spec.md"])
    worker_a = DAGNode(id="worker-a", type=NodeType.WORKER, prompt="Backend", inputs=["spec.md"])
    worker_b = DAGNode(id="worker-b", type=NodeType.WORKER, prompt="Frontend", inputs=["spec.md"])
    verifier = DAGNode(id="verifier", type=NodeType.VERIFIER, prompt="Audit", inputs=["worker-a", "worker-b"])

    wf = WorkflowSpec(version="1.0", name="Parallel Flow", nodes=[planner, worker_a, worker_b, verifier])
    waves = DAGOptimizer.compute_parallel_waves(wf)

    assert len(waves) == 3
    # Wave 0: planner
    assert [n.id for n in waves[0]] == ["planner"]
    # Wave 1: worker-a and worker-b parallel fan-out
    wave_1_ids = sorted([n.id for n in waves[1]])
    assert wave_1_ids == ["worker-a", "worker-b"]
    # Wave 2: verifier
    assert [n.id for n in waves[2]] == ["verifier"]


def test_cycle_detection_raises_error():
    node_a = DAGNode(id="node-a", type=NodeType.WORKER, prompt="A", inputs=["node-b"])
    node_b = DAGNode(id="node-b", type=NodeType.WORKER, prompt="B", inputs=["node-a"])

    wf = WorkflowSpec(version="1.0", name="Cyclic Flow", nodes=[node_a, node_b])
    with pytest.raises(GraphOptimizationError, match="Cyclic dependency detected"):
        DAGOptimizer.compute_parallel_waves(wf)


def test_dag_engine_dry_run():
    planner = DAGNode(id="planner", type=NodeType.PLANNER, prompt="Design", outputs=["schema.json"])
    worker = DAGNode(id="worker", type=NodeType.WORKER, prompt="Build", inputs=["schema.json"])
    wf = WorkflowSpec(version="1.0", name="Dry Run Flow", nodes=[planner, worker])

    engine = DAGEngine(concurrency_limit=2)
    result = engine.run_workflow(wf, dry_run=True)

    assert result.success is True
    assert len(result.node_results) == 2
    assert result.node_results["planner"].status.value == "success"
    assert result.node_results["worker"].status.value == "success"
