"""False-edge pruner and topological wave optimizer for AgentGraph DAGs."""
from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, List, Set, Tuple

from src.graph.types import DAGNode, WorkflowSpec


class GraphOptimizationError(Exception):
    """Raised when graph optimization or cycle detection fails."""
    pass


class DAGOptimizer:
    """Optimizes workflow execution graphs by pruning false edges and grouping into parallel waves."""

    @staticmethod
    def build_dependency_graph(workflow: WorkflowSpec) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """
        Builds adjacency and reverse adjacency maps based strictly on true data dependencies:
        1. Node B directly references Node A in inputs.
        2. Node B lists an input file that is an output of Node A.

        Returns:
            (dependencies, dependents)
            dependencies[node_id] = set of node_ids that must finish before node_id
            dependents[node_id] = set of node_ids waiting for node_id
        """
        node_map: Dict[str, DAGNode] = {node.id: node for node in workflow.nodes}
        node_ids = set(node_map.keys())

        # Map file paths -> producing node_id
        output_to_producer: Dict[str, str] = {}
        for node in workflow.nodes:
            for out in node.outputs:
                output_to_producer[out] = node.id

        dependencies: Dict[str, Set[str]] = {node.id: set() for node in workflow.nodes}
        dependents: Dict[str, Set[str]] = {node.id: set() for node in workflow.nodes}

        for node in workflow.nodes:
            for inp in node.inputs:
                # Direct node reference
                if inp in node_ids and inp != node.id:
                    dependencies[node.id].add(inp)
                    dependents[inp].add(node.id)
                # Output file reference from another node
                elif inp in output_to_producer:
                    producer_id = output_to_producer[inp]
                    if producer_id != node.id:
                        dependencies[node.id].add(producer_id)
                        dependents[producer_id].add(node.id)

        return dependencies, dependents

    @staticmethod
    def detect_cycles(dependencies: Dict[str, Set[str]]) -> None:
        """Kahn's algorithm to detect cycles in the graph."""
        in_degrees = {node_id: len(deps) for node_id, deps in dependencies.items()}
        queue = deque([node_id for node_id, deg in in_degrees.items() if deg == 0])
        visited_count = 0

        # Build dependents map for traversal
        dependents: Dict[str, Set[str]] = defaultdict(set)
        for node_id, deps in dependencies.items():
            for dep in deps:
                dependents[dep].add(node_id)

        while queue:
            curr = queue.popleft()
            visited_count += 1
            for dependent in dependents[curr]:
                in_degrees[dependent] -= 1
                if in_degrees[dependent] == 0:
                    queue.append(dependent)

        if visited_count != len(dependencies):
            unresolved = [node_id for node_id, deg in in_degrees.items() if deg > 0]
            raise GraphOptimizationError(
                f"Cyclic dependency detected in workflow graph! Unresolved nodes in cycle: {unresolved}"
            )

    @staticmethod
    def compute_parallel_waves(workflow: WorkflowSpec) -> List[List[DAGNode]]:
        """
        Decomposes the DAG into parallel execution waves (levels) after pruning false edges.
        Nodes within the same wave have all dependencies resolved by previous waves
        and can be executed concurrently up to CONCURRENCY_LIMIT.
        """
        dependencies, dependents = DAGOptimizer.build_dependency_graph(workflow)
        DAGOptimizer.detect_cycles(dependencies)

        node_map = {node.id: node for node in workflow.nodes}
        in_degrees = {node_id: len(deps) for node_id, deps in dependencies.items()}

        waves: List[List[DAGNode]] = []
        current_wave = [node_id for node_id, deg in in_degrees.items() if deg == 0]

        while current_wave:
            # Sort for deterministic execution ordering
            current_wave.sort()
            wave_nodes = [node_map[nid] for nid in current_wave]
            waves.append(wave_nodes)

            next_wave: List[str] = []
            for nid in current_wave:
                for dependent in dependents[nid]:
                    in_degrees[dependent] -= 1
                    if in_degrees[dependent] == 0:
                        next_wave.append(dependent)

            current_wave = next_wave

        return waves
