"""Type specifications and data models for AgentGraph workflow DAGs."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    PLANNER = "planner"
    WORKER = "worker"
    VERIFIER = "verifier"
    DREAM = "dream"
    SYNTHESIZER = "synthesizer"


class GateMode(str, Enum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VerificationSpec:
    command: str
    timeout_seconds: int = 120


@dataclass
class DAGNode:
    id: str
    type: NodeType
    prompt: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    worktree: bool = False
    verification: Optional[VerificationSpec] = None
    gate: GateMode = GateMode.BLOCKING
    fresh_context: bool = False
    target: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowSpec:
    version: str
    name: str
    nodes: List[DAGNode] = field(default_factory=list)

    def get_node(self, node_id: str) -> Optional[DAGNode]:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None


@dataclass
class NodeResult:
    node_id: str
    status: NodeStatus
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    produced_outputs: List[str] = field(default_factory=list)
    worktree_path: Optional[str] = None
    diff: str = ""
    message: str = ""


@dataclass
class WorkflowResult:
    workflow_name: str
    success: bool
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    total_duration_seconds: float = 0.0
    error: Optional[str] = None
