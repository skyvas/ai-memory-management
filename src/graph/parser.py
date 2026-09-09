"""YAML parser and schema validator for AgentGraph workflow specifications."""
from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Union
import yaml

from src.graph.types import DAGNode, GateMode, NodeType, VerificationSpec, WorkflowSpec


class WorkflowParserError(Exception):
    """Raised when a workflow specification fails validation."""
    pass


class WorkflowParser:
    """Parses and validates workflow YAML specifications."""

    @staticmethod
    def parse_file(file_path: Union[str, Path]) -> WorkflowSpec:
        """Parse workflow from a YAML file path."""
        path = Path(file_path)
        if not path.exists():
            raise WorkflowParserError(f"Workflow file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise WorkflowParserError(f"Failed to parse YAML file {file_path}: {e}") from e

        return WorkflowParser.parse_dict(data)

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> WorkflowSpec:
        """Parse workflow from a raw dictionary."""
        if not isinstance(data, dict):
            raise WorkflowParserError("Workflow root must be a dictionary/mapping.")

        version = str(data.get("version", "1.0"))
        name = str(data.get("name", "Unnamed Workflow"))

        raw_nodes = data.get("nodes", [])
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise WorkflowParserError("Workflow must contain a non-empty 'nodes' list.")

        nodes: List[DAGNode] = []
        seen_ids = set()

        for idx, node_data in enumerate(raw_nodes):
            if not isinstance(node_data, dict):
                raise WorkflowParserError(f"Node at index {idx} must be a dictionary.")

            node_id = str(node_data.get("id", "")).strip()
            if not node_id:
                raise WorkflowParserError(f"Node at index {idx} is missing required 'id'.")
            if node_id in seen_ids:
                raise WorkflowParserError(f"Duplicate node ID detected: '{node_id}'.")
            seen_ids.add(node_id)

            raw_type = str(node_data.get("type", "worker")).strip().lower()
            try:
                node_type = NodeType(raw_type)
            except ValueError:
                valid_types = [t.value for t in NodeType]
                raise WorkflowParserError(
                    f"Node '{node_id}' has invalid type '{raw_type}'. Valid types: {valid_types}"
                )

            prompt = str(node_data.get("prompt", "")).strip()
            inputs = [str(i) for i in node_data.get("inputs", [])]
            outputs = [str(o) for o in node_data.get("outputs", [])]
            worktree = bool(node_data.get("worktree", False))

            # Verification spec
            verification: Union[VerificationSpec, None] = None
            raw_verify = node_data.get("verification")
            if raw_verify:
                if isinstance(raw_verify, dict) and "command" in raw_verify:
                    verification = VerificationSpec(
                        command=str(raw_verify["command"]),
                        timeout_seconds=int(raw_verify.get("timeout_seconds", 120))
                    )
                elif isinstance(raw_verify, str):
                    verification = VerificationSpec(command=raw_verify)

            # Gate mode
            raw_gate = str(node_data.get("gate", "blocking")).strip().lower()
            gate = GateMode.ADVISORY if raw_gate == "advisory" else GateMode.BLOCKING

            # Fresh context flag (camelCase or snake_case)
            fresh_context = bool(node_data.get("freshContext", node_data.get("fresh_context", False)))
            target = node_data.get("target")

            nodes.append(
                DAGNode(
                    id=node_id,
                    type=node_type,
                    prompt=prompt,
                    inputs=inputs,
                    outputs=outputs,
                    worktree=worktree,
                    verification=verification,
                    gate=gate,
                    fresh_context=fresh_context,
                    target=target,
                    metadata={k: v for k, v in node_data.items() if k not in {
                        "id", "type", "prompt", "inputs", "outputs", "worktree",
                        "verification", "gate", "freshContext", "fresh_context", "target"
                    }}
                )
            )

        return WorkflowSpec(version=version, name=name, nodes=nodes)
