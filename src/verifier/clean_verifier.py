"""Pristine-context verifier executing out-of-band audits without past reasoning bias."""
from __future__ import annotations
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Callable, List, Optional

from src.loop.verifier_gate import GateResult, VerifierGate


@dataclass
class AuditResult:
    approved: bool
    is_blocking: bool
    feedback: List[str] = field(default_factory=list)
    security_findings: List[str] = field(default_factory=list)
    gate_result: Optional[GateResult] = None
    summary: str = ""


class CleanVerifier:
    """Audits unified git diffs in a pristine context window against requirements."""

    RISK_PATTERNS = [
        (r"eval\(", "Critical: Insecure eval() statement detected."),
        (r"password\s*=\s*['\"][^'\"]+['\"]", "Security: Hardcoded credentials or password found in diff."),
        (r"SELECT\s+.*\s+FROM\s+.*\s+WHERE\s+.*=.*%.*", "Security: Potential raw SQL string interpolation instead of parameterized query."),
        (r":memory:", "Concurrency: In-memory SQLite detected under concurrent test harness (FP-014 violation)."),
    ]

    def __init__(self, llm_fn: Optional[Callable[[str, str], str]] = None):
        self.llm_fn = llm_fn

    def audit_diff(
        self,
        specification: str,
        unified_diff: str,
        verify_cmd: Optional[str] = None,
        is_blocking: bool = True,
        cwd: Optional[Path] = None
    ) -> AuditResult:
        """
        Conducts a clean-room audit of the raw unified diff against the specification.
        Checks for security issues, regressions, and runs optional verification commands.
        """
        feedback: List[str] = []
        security_findings: List[str] = []

        # 1. Static risk pattern scan
        for pattern, warning in self.RISK_PATTERNS:
            if re.search(pattern, unified_diff, re.IGNORECASE):
                security_findings.append(warning)

        # 2. Run deterministic verification gate if specified
        gate_res: Optional[GateResult] = None
        if verify_cmd:
            gate_res = VerifierGate.run_command(verify_cmd, cwd=cwd)
            if not gate_res.passed:
                feedback.append(
                    f"Verification gate '{verify_cmd}' failed with exit code {gate_res.exit_code}:\n{gate_res.stderr.strip()}"
                )

        # 3. LLM pristine review if LLM available
        if self.llm_fn and unified_diff.strip():
            system_prompt = (
                "You are an adversarial, pristine-context verification auditor with zero past bias. "
                "Evaluate the unified diff strictly against requirements. Identify bugs, concurrency hazards, "
                "or security flaws."
            )
            prompt = f"Specification:\n{specification}\n\nUnified Diff:\n{unified_diff[:4000]}"
            llm_review = self.llm_fn(prompt, system_prompt)
            if "REJECT" in llm_review.upper():
                feedback.append(f"Adversarial Verifier rejection: {llm_review}")

        # Approval logic
        has_critical_security = any("Critical" in f or "Hardcoded" in f for f in security_findings)
        gate_failed = (gate_res is not None and not gate_res.passed)

        approved = not (has_critical_security or gate_failed)

        status_str = "APPROVED" if approved else "REJECTED"
        summary = (
            f"Verifier Gate: {status_str} | "
            f"Findings: {len(security_findings)} security items, {len(feedback)} feedback items."
        )

        return AuditResult(
            approved=approved,
            is_blocking=is_blocking,
            feedback=feedback,
            security_findings=security_findings,
            gate_result=gate_res,
            summary=summary
        )
