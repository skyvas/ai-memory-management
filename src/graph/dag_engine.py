"""Topological DAG execution engine with concurrent wave dispatch and isolation."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional

from src.graph.optimizer import DAGOptimizer
from src.graph.types import DAGNode, GateMode, NodeResult, NodeStatus, NodeType, WorkflowResult, WorkflowSpec
from src.harness.git_worktree import GitWorktreeManager
from src.loop.agent_loop import AgentLoop
from src.loop.verifier_gate import VerifierGate
from src.memory.dreaming_engine import DreamingEngine
from src.verifier.clean_verifier import CleanVerifier


class DAGEngineError(Exception):
    """Raised when DAG execution fails or a blocking gate rejects progress."""
    pass


class DAGEngine:
    """Executes workflow Directed Acyclic Graphs across parallel execution waves."""

    def __init__(
        self,
        concurrency_limit: Optional[int] = None,
        repo_root: Optional[Path] = None,
        worktree_manager: Optional[GitWorktreeManager] = None,
        dreaming_engine: Optional[DreamingEngine] = None,
        verifier: Optional[CleanVerifier] = None,
        verbose: bool = False
    ):
        self.concurrency_limit = concurrency_limit or int(os.environ.get("CONCURRENCY_LIMIT", 4))
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.worktree_manager = worktree_manager or GitWorktreeManager(repo_root=self.repo_root)
        self.dreaming_engine = dreaming_engine or DreamingEngine()
        self.verifier = verifier or CleanVerifier()
        self.verbose = verbose

    def _execute_single_node(
        self,
        node: DAGNode,
        workflow: WorkflowSpec,
        dry_run: bool = False,
        node_results: Optional[Dict[str, NodeResult]] = None
    ) -> NodeResult:
        """Executes a single node inside its worktree or root directory."""
        start_time = time.perf_counter()
        target_dir = self.repo_root
        wt_path: Optional[str] = None

        if self.verbose:
            print(f"[*] Starting node: {node.id} ({node.type.value})")

        # 1. Handle worktree isolation if requested
        if node.worktree and not dry_run:
            try:
                created_path = self.worktree_manager.create_worktree(node.id)
                target_dir = created_path
                wt_path = str(created_path)
            except Exception as e:
                return NodeResult(
                    node_id=node.id,
                    status=NodeStatus.FAILED,
                    exit_code=1,
                    duration_seconds=time.perf_counter() - start_time,
                    message=f"Worktree allocation failed: {e}"
                )

        if dry_run:
            duration = time.perf_counter() - start_time
            return NodeResult(
                node_id=node.id,
                status=NodeStatus.SUCCESS,
                exit_code=0,
                duration_seconds=duration,
                worktree_path=wt_path,
                produced_outputs=node.outputs,
                message=f"[DRY-RUN] Simulated execution for node {node.id}"
            )

        # 2. Dispatch based on node type
        try:
            if node.type == NodeType.PLANNER:
                # Planners formulate specs and contracts
                for out_file in node.outputs:
                    out_path = target_dir / out_file
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    if not out_path.exists():
                        out_path.write_text(f"# Generated Contract for {node.id}\n\n{node.prompt}\n")

                exit_code = 0
                stdout = f"Generated {len(node.outputs)} output contract(s)."
                stderr = ""

                # Verification check if declared
                if node.verification:
                    gate_res = VerifierGate.run_command(node.verification.command, cwd=target_dir)
                    exit_code = gate_res.exit_code
                    stdout += f"\n{gate_res.stdout}"
                    stderr = gate_res.stderr

                status = NodeStatus.SUCCESS if exit_code == 0 else NodeStatus.FAILED
                return NodeResult(
                    node_id=node.id,
                    status=status,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=time.perf_counter() - start_time,
                    produced_outputs=node.outputs,
                    worktree_path=wt_path,
                    message=f"Planner completed with exit code {exit_code}"
                )

            elif node.type == NodeType.WORKER:
                # Worker runs the autonomous loop against verification gate
                verify_cmd = node.verification.command if node.verification else "echo OK"
                loop = AgentLoop(max_iterations=int(os.environ.get("MAX_LOOP_ITERATIONS", 15)))
                loop_res = loop.run(goal=node.prompt, verify_cmd=verify_cmd, workdir=target_dir)

                status = NodeStatus.SUCCESS if loop_res.success else NodeStatus.FAILED
                exit_code = loop_res.final_gate_result.exit_code if loop_res.final_gate_result else (0 if loop_res.success else 1)

                return NodeResult(
                    node_id=node.id,
                    status=status,
                    exit_code=exit_code,
                    stdout=f"Completed in {loop_res.iterations_completed} iterations.",
                    stderr=loop_res.final_gate_result.stderr if loop_res.final_gate_result else "",
                    duration_seconds=time.perf_counter() - start_time,
                    produced_outputs=node.outputs,
                    worktree_path=wt_path,
                    message=loop_res.message
                )

            elif node.type == NodeType.VERIFIER:
                # Pristine verifier reviews predecessor diffs
                combined_diff = ""
                # Collect predecessor diffs
                if node_results:
                    for inp in node.inputs:
                        if inp in node_results and node_results[inp].diff:
                            combined_diff += f"\n--- Diff from {inp} ---\n{node_results[inp].diff}\n"

                verify_cmd = node.verification.command if node.verification else None
                audit_res = self.verifier.audit_diff(
                    specification=node.prompt,
                    unified_diff=combined_diff,
                    verify_cmd=verify_cmd,
                    is_blocking=(node.gate == GateMode.BLOCKING),
                    cwd=target_dir
                )

                status = NodeStatus.SUCCESS if audit_res.approved else NodeStatus.FAILED
                exit_code = 0 if audit_res.approved else 1

                return NodeResult(
                    node_id=node.id,
                    status=status,
                    exit_code=exit_code,
                    stdout=audit_res.summary,
                    stderr="\n".join(audit_res.feedback),
                    duration_seconds=time.perf_counter() - start_time,
                    message=audit_res.summary
                )

            elif node.type == NodeType.DREAM:
                # Dreaming consolidation phase
                dream_res = self.dreaming_engine.run_dreaming_cycle(sync_gemini=True)
                return NodeResult(
                    node_id=node.id,
                    status=NodeStatus.SUCCESS,
                    exit_code=0,
                    stdout=dream_res.summary,
                    duration_seconds=time.perf_counter() - start_time,
                    message=dream_res.summary
                )

            elif node.type == NodeType.SYNTHESIZER:
                # Merge worktrees and run integration checks
                verify_cmd = node.verification.command if node.verification else "echo Synthesis complete"
                gate_res = VerifierGate.run_command(verify_cmd, cwd=self.repo_root)

                # Clean active worktrees if configured
                cleaned = self.worktree_manager.clean_all_task_worktrees(force=True)

                status = NodeStatus.SUCCESS if gate_res.passed else NodeStatus.FAILED
                return NodeResult(
                    node_id=node.id,
                    status=status,
                    exit_code=gate_res.exit_code,
                    stdout=f"{gate_res.stdout}\nCleaned {cleaned} temporary worktree(s).",
                    stderr=gate_res.stderr,
                    duration_seconds=time.perf_counter() - start_time,
                    message="Synthesizer pass completed."
                )

            else:
                return NodeResult(
                    node_id=node.id,
                    status=NodeStatus.FAILED,
                    exit_code=1,
                    message=f"Unsupported node type: {node.type}"
                )

        except Exception as e:
            return NodeResult(
                node_id=node.id,
                status=NodeStatus.FAILED,
                exit_code=1,
                duration_seconds=time.perf_counter() - start_time,
                message=f"Execution error on node {node.id}: {e}"
            )

    def run_workflow(self, workflow: WorkflowSpec, dry_run: bool = False) -> WorkflowResult:
        """
        Executes a workflow by decomposing into parallel waves,
        dispatching concurrent workers, enforcing blocking gates, and recording results.
        """
        start_time = time.perf_counter()
        waves = DAGOptimizer.compute_parallel_waves(workflow)
        node_results: Dict[str, NodeResult] = {}

        if self.verbose:
            print(f"[*] Optimizing DAG: Decomposed into {len(waves)} parallel execution wave(s).")
            for idx, wave in enumerate(waves):
                print(f"    Wave {idx + 1}: {[n.id for n in wave]}")

        for wave_idx, wave in enumerate(waves):
            if self.verbose:
                print(f"\n[=== Executing Wave {wave_idx + 1}/{len(waves)} ({len(wave)} node(s)) ===]")

            # Run wave nodes concurrently up to concurrency_limit
            max_workers = min(len(wave), self.concurrency_limit)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_node = {
                    executor.submit(
                        self._execute_single_node, node, workflow, dry_run, node_results
                    ): node
                    for node in wave
                }

                for future in as_completed(future_to_node):
                    node = future_to_node[future]
                    try:
                        res = future.result()
                    except Exception as exc:
                        res = NodeResult(
                            node_id=node.id,
                            status=NodeStatus.FAILED,
                            exit_code=1,
                            message=f"Unhandled exception: {exc}"
                        )

                    node_results[node.id] = res

                    if self.verbose:
                        print(f"    -> Node {node.id}: {res.status.value} (exit code {res.exit_code})")

                    # Check if blocking gate failed
                    if res.status == NodeStatus.FAILED and node.gate == GateMode.BLOCKING:
                        total_duration = time.perf_counter() - start_time
                        return WorkflowResult(
                            workflow_name=workflow.name,
                            success=False,
                            node_results=node_results,
                            total_duration_seconds=total_duration,
                            error=f"Workflow aborted: Blocking gate failed on node '{node.id}': {res.message}"
                        )

        total_duration = time.perf_counter() - start_time
        return WorkflowResult(
            workflow_name=workflow.name,
            success=True,
            node_results=node_results,
            total_duration_seconds=total_duration
        )
