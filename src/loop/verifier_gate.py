"""Deterministic Verification Gates enforcing binary truth via process exit codes."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Optional


@dataclass
class GateResult:
    command: str
    exit_code: int
    passed: bool
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def summary(self) -> str:
        status = "PASSED (exit code 0)" if self.passed else f"FAILED (exit code {self.exit_code})"
        return f"Gate '{self.command}': {status} in {self.duration_seconds:.2f}s"


class VerifierGate:
    """Executes verification commands and validates that process exit code is 0."""

    @staticmethod
    def run_command(
        command: str,
        cwd: Optional[Path] = None,
        timeout_seconds: int = 120
    ) -> GateResult:
        """
        Executes a verification shell command, measuring duration and capturing
        process return code as the objective verification gate.
        """
        start = time.perf_counter()
        target_cwd = cwd or Path.cwd()

        env = os.environ.copy()
        venv_bin = str(Path(sys.executable).parent)
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"

        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(target_cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env
            )
            duration = time.perf_counter() - start
            passed = (res.returncode == 0)
            return GateResult(
                command=command,
                exit_code=res.returncode,
                passed=passed,
                stdout=res.stdout,
                stderr=res.stderr,
                duration_seconds=duration
            )
        except subprocess.TimeoutExpired as e:
            duration = time.perf_counter() - start
            return GateResult(
                command=command,
                exit_code=124,  # Standard timeout exit code
                passed=False,
                stdout=e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""),
                stderr=f"Verification gate timed out after {timeout_seconds} seconds.",
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.perf_counter() - start
            return GateResult(
                command=command,
                exit_code=1,
                passed=False,
                stdout="",
                stderr=f"Failed to execute gate: {e}",
                duration_seconds=duration
            )
