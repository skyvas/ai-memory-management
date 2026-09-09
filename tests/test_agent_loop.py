"""Tests for AgentLoop heartbeat, verification gates, and token monitoring."""
from pathlib import Path
import sys
import pytest

from src.loop.agent_loop import AgentLoop
from src.loop.verifier_gate import VerifierGate
from src.loop.token_budget import TokenBudgetMonitor


def test_verifier_gate_exit_code_zero():
    res = VerifierGate.run_command(f'"{sys.executable}" -c \'print("success")\'')
    assert res.passed is True
    assert res.exit_code == 0
    assert "success" in res.stdout


def test_verifier_gate_non_zero_exit_code():
    res = VerifierGate.run_command(f'"{sys.executable}" -c \'import sys; sys.exit(42)\'')
    assert res.passed is False
    assert res.exit_code == 42


def test_token_budget_monitor_alert_threshold():
    monitor = TokenBudgetMonitor(alert_threshold=1000)
    monitor.record_usage(prompt_tokens=400, completion_tokens=200, iteration=1)
    assert not monitor.is_threshold_exceeded()

    monitor.record_usage(prompt_tokens=300, completion_tokens=200, iteration=2)
    assert monitor.is_threshold_exceeded()
    rec = monitor.get_compaction_recommendation()
    assert rec is not None
    assert "ALERT" in rec


def test_agent_loop_self_healing_success(tmp_path: Path):
    """
    Test loop self-repair:
    Iteration 1 fails, Iteration 2 fixes file and passes.
    """
    counter_file = tmp_path / "attempt.txt"
    counter_file.write_text("0")

    # Command fails on first run, creates success condition on second
    verify_cmd = (
        f'"{sys.executable}" -c \'from pathlib import Path; '
        f'p = Path("{counter_file}"); v = int(p.read_text()); '
        f'p.write_text(str(v+1)); exit(0 if v >= 1 else 1)\''
    )

    loop = AgentLoop(max_iterations=5)
    result = loop.run(goal="Make test pass", verify_cmd=verify_cmd, workdir=tmp_path)

    assert result.success is True
    assert result.iterations_completed == 2
    assert result.final_gate_result is not None
    assert result.final_gate_result.exit_code == 0
