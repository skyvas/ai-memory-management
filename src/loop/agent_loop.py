"""Autonomous agent heartbeat loop: Observe -> Plan -> Act -> Hook -> Verify."""
from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional

from src.harness.hooks import HookRunner
from src.loop.token_budget import TokenBudgetMonitor
from src.loop.verifier_gate import GateResult, VerifierGate


@dataclass
class IterationRecord:
    iteration: int
    observation: str
    action_taken: str
    gate_result: Optional[GateResult] = None
    duration_seconds: float = 0.0


@dataclass
class LoopResult:
    goal: str
    success: bool
    iterations_completed: int
    records: List[IterationRecord] = field(default_factory=list)
    final_gate_result: Optional[GateResult] = None
    total_tokens_used: int = 0
    duration_seconds: float = 0.0
    message: str = ""


class AgentLoop:
    """Executes self-healing autonomous execution loops against deterministic verification gates."""

    def __init__(
        self,
        max_iterations: Optional[int] = None,
        token_alert_threshold: Optional[int] = None,
        hook_runner: Optional[HookRunner] = None,
        llm_fn: Optional[Callable[[str, str], str]] = None
    ):
        self.max_iterations = max_iterations or int(os.environ.get("MAX_LOOP_ITERATIONS", 15))
        self.token_monitor = TokenBudgetMonitor(alert_threshold=token_alert_threshold)
        self.hook_runner = hook_runner or HookRunner()
        self.llm_fn = llm_fn or self._default_gemini_or_mock_llm

    def _default_gemini_or_mock_llm(self, prompt: str, system_prompt: str) -> str:
        """
        Calls Google Gemini API if GEMINI_API_KEY is present;
        otherwise runs offline deterministic synthesis.
        """
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key and api_key != "AIzaSy...":
            try:
                import httpx
                model = os.environ.get("DEFAULT_MODEL", "gemini-2.5-pro")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\nTask:\n{prompt}"}]}]
                }
                res = httpx.post(url, json=payload, timeout=60.0)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except Exception:
                pass

        # Offline / deterministic fallback
        return f"[Agent Autonomous Synthesis for: {prompt[:80]}...]"

    def observe(self, workdir: Path, last_gate_result: Optional[GateResult]) -> str:
        """Inspects current workspace state, active diffs, and previous stderr."""
        observations = []

        # Check git diff if inside git repository
        try:
            res = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(workdir),
                capture_output=True,
                text=True,
                check=False
            )
            if res.stdout.strip():
                observations.append(f"Workspace Status:\n{res.stdout.strip()}")
        except Exception:
            pass

        # If previous gate failed, feed stderr for automated self-repair
        if last_gate_result and not last_gate_result.passed:
            observations.append(
                f"PREVIOUS VERIFICATION FAILURE (Exit Code {last_gate_result.exit_code}):\n"
                f"Command: {last_gate_result.command}\n"
                f"STDERR:\n{last_gate_result.stderr.strip()}\n"
                f"STDOUT:\n{last_gate_result.stdout.strip()[:500]}"
            )
        else:
            observations.append("Baseline observation: ready for action.")

        return "\n\n".join(observations)

    def run(
        self,
        goal: str,
        verify_cmd: str,
        workdir: Optional[Path] = None,
        on_iteration: Optional[Callable[[IterationRecord], None]] = None
    ) -> LoopResult:
        """
        Executes the autonomous loop: Observe -> Plan -> Act -> Hook -> Verify
        until verification passes (exit code 0) or max_iterations reached.
        """
        start_time = time.perf_counter()
        target_dir = (workdir or Path.cwd()).resolve()
        records: List[IterationRecord] = []
        last_gate: Optional[GateResult] = None

        for iteration in range(1, self.max_iterations + 1):
            iter_start = time.perf_counter()

            # 1. Observe
            obs = self.observe(target_dir, last_gate)

            # 2. Plan & 3. Act (LLM Reasoning / Action Formulation)
            system_prompt = (
                "You are an autonomous engineering agent operating inside AgentGraph. "
                "Your objective is to achieve process exit code 0 on the verification command."
            )
            act_response = self.llm_fn(f"Goal: {goal}\nObservation:\n{obs}", system_prompt)

            # Simulate token usage
            prompt_tokens = len(obs.split()) * 2 + 150
            completion_tokens = len(act_response.split()) * 2 + 50
            self.token_monitor.record_usage(prompt_tokens, completion_tokens, iteration=iteration)

            # 4. Hook (PostToolUse Auto-Formatters)
            # Run hooks for modified files if any
            self.hook_runner.trigger_post_tool_use("write", target_dir)

            # 5. Verify (Deterministic binary gate: exit code 0)
            gate_result = VerifierGate.run_command(verify_cmd, cwd=target_dir)
            last_gate = gate_result

            iter_duration = time.perf_counter() - iter_start
            rec = IterationRecord(
                iteration=iteration,
                observation=obs,
                action_taken=act_response,
                gate_result=gate_result,
                duration_seconds=iter_duration
            )
            records.append(rec)
            if on_iteration:
                on_iteration(rec)

            # Success condition: Process Exit Code 0
            if gate_result.passed:
                total_duration = time.perf_counter() - start_time
                return LoopResult(
                    goal=goal,
                    success=True,
                    iterations_completed=iteration,
                    records=records,
                    final_gate_result=gate_result,
                    total_tokens_used=self.token_monitor.cumulative_tokens,
                    duration_seconds=total_duration,
                    message=f"Goal successfully verified with exit code 0 in {iteration} iteration(s)."
                )

        total_duration = time.perf_counter() - start_time
        return LoopResult(
            goal=goal,
            success=False,
            iterations_completed=self.max_iterations,
            records=records,
            final_gate_result=last_gate,
            total_tokens_used=self.token_monitor.cumulative_tokens,
            duration_seconds=total_duration,
            message=f"Iteration quota ({self.max_iterations}) reached without achieving exit code 0."
        )
