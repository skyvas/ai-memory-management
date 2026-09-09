"""AgentGraph CLI entrypoint for loops, graphs, dreaming, and worktree operations."""
from __future__ import annotations
import os
from pathlib import Path
import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.graph.parser import WorkflowParser
from src.graph.dag_engine import DAGEngine
from src.harness.git_worktree import GitWorktreeManager
from src.loop.agent_loop import AgentLoop
from src.memory.dreaming_engine import DreamingEngine
from src.memory.markdown_memory import MarkdownMemoryManager

console = Console()


@click.group()
def cli():
    """AgentGraph: Autonomous Loop, Graph & Memory Engineering Harness."""
    pass


@cli.command("run-graph")
@click.argument("workflow_path", type=click.Path(exists=True))
@click.option("--concurrency", "-c", type=int, default=None, help="Maximum concurrent worker nodes.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose debug logs.")
@click.option("--dry-run", is_flag=True, help="Simulate DAG optimization and wave dispatch without side effects.")
def run_graph(workflow_path: str, concurrency: int, verbose: bool, dry_run: bool):
    """Execute a multi-stage workflow Directed Acyclic Graph."""
    console.print(Panel(f"[bold cyan]AgentGraph Engine[/bold cyan] :: Executing DAG [yellow]{workflow_path}[/yellow]"))
    try:
        workflow = WorkflowParser.parse_file(workflow_path)
    except Exception as e:
        console.print(f"[bold red]Validation Error:[/bold red] {e}")
        sys.exit(1)

    engine = DAGEngine(concurrency_limit=concurrency, verbose=verbose)
    result = engine.run_workflow(workflow, dry_run=dry_run)

    table = Table(title=f"Workflow Results: {workflow.name}", show_header=True, header_style="bold magenta")
    table.add_column("Node ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Exit Code", justify="right")
    table.add_column("Duration", justify="right")
    table.add_column("Notes", style="dim")

    for node_id, res in result.node_results.items():
        status_color = "green" if res.status.value == "success" else "red"
        table.add_row(
            node_id,
            f"[{status_color}]{res.status.value.upper()}[/{status_color}]",
            str(res.exit_code),
            f"{res.duration_seconds:.2f}s",
            res.message[:60]
        )

    console.print(table)

    if result.success:
        console.print(f"[bold green]✓ Workflow completed successfully in {result.total_duration_seconds:.2f}s.[/bold green]")
        sys.exit(0)
    else:
        console.print(f"[bold red]✗ Workflow failed:[/bold red] {result.error}")
        sys.exit(1)


@cli.command("run-loop")
@click.option("--goal", "-g", required=True, help="Target objective for the autonomous loop.")
@click.option("--verify-cmd", "-v", required=True, help="Deterministic verification gate command (exit code 0).")
@click.option("--max-retries", "-m", type=int, default=10, help="Maximum loop iterations.")
@click.option("--isolated-worktree", is_flag=True, help="Execute loop inside an isolated Git Worktree.")
def run_loop(goal: str, verify_cmd: str, max_retries: int, isolated_worktree: bool):
    """Launch a targeted self-healing loop against a deterministic verification gate."""
    console.print(Panel(f"[bold cyan]AgentGraph Loop[/bold cyan] :: Goal: [italic]{goal}[/italic]\nGate: [yellow]{verify_cmd}[/yellow]"))

    workdir = None
    wt_manager = None
    task_id = "targeted-loop"

    if isolated_worktree:
        wt_manager = GitWorktreeManager()
        try:
            workdir = wt_manager.create_worktree(task_id)
            console.print(f"[blue][*] Provisioned isolated worktree at:[/blue] {workdir}")
        except Exception as e:
            console.print(f"[bold yellow]Warning:[/bold yellow] Worktree allocation failed ({e}), using current directory.")

    loop = AgentLoop(max_iterations=max_retries)
    res = loop.run(goal=goal, verify_cmd=verify_cmd, workdir=workdir)

    if isolated_worktree and wt_manager and workdir:
        wt_manager.remove_worktree(task_id, force=True)
        console.print("[dim][*] Cleaned temporary worktree.[/dim]")

    if res.success:
        console.print(f"[bold green]✓ Verified exit code 0 achieved in {res.iterations_completed} iterations ({res.duration_seconds:.2f}s).[/bold green]")
        sys.exit(0)
    else:
        console.print(f"[bold red]✗ Verification failed:[/bold red] {res.message}")
        if res.final_gate_result and res.final_gate_result.stderr:
            console.print(f"[red]Stderr:[/red]\n{res.final_gate_result.stderr}")
        sys.exit(1)


@cli.command("dream")
@click.option("--trace-dir", type=click.Path(), default=".logs/sessions", help="Path to session trace logs.")
@click.option("--memory-dir", type=click.Path(), default=".memory", help="Path to Markdown memory directory.")
@click.option("--sync-gemini", is_flag=True, default=True, help="Synchronize distilled rules into GEMINI.md.")
@click.option("--sync-claude", is_flag=True, help="Backward-compatibility flag for sync-gemini.")
@click.option("--prune-transient", is_flag=True, default=True, help="Prune transient episodic logs after consolidation.")
def dream(trace_dir: str, memory_dir: str, sync_gemini: bool, sync_claude: bool, prune_transient: bool):
    """Execute offline memory consolidation ('Dreaming') to update Markdown memory."""
    console.print(Panel("[bold cyan]AgentGraph Dreaming Engine[/bold cyan] :: Consolidating episodic logs into .memory/"))

    mem_manager = MarkdownMemoryManager(memory_dir=Path(memory_dir))
    engine = DreamingEngine(memory_manager=mem_manager, trace_dir=Path(trace_dir))

    do_sync = sync_gemini or sync_claude
    result = engine.run_dreaming_cycle(sync_gemini=do_sync, prune_transient=prune_transient)

    console.print(f"[bold green]✓ {result.summary}[/bold green]")


@cli.command("worktrees:list")
def worktrees_list():
    """List all active agent Git Worktrees."""
    wt_manager = GitWorktreeManager()
    wts = wt_manager.list_worktrees()

    table = Table(title="Active Git Worktrees", show_header=True, header_style="bold cyan")
    table.add_column("Path", style="dim")
    table.add_column("Head Commit", style="yellow")
    table.add_column("Branch", style="green")

    for wt in wts:
        table.add_row(wt.path, wt.head[:8] if wt.head else "", wt.branch or "(detached)")

    console.print(table)


@cli.command("worktrees:clean")
@click.option("--force", "-f", is_flag=True, help="Force cleanup of all task worktrees.")
def worktrees_clean(force: bool):
    """Prune inactive worktrees and orphaned agent branches."""
    wt_manager = GitWorktreeManager()
    cleaned = wt_manager.clean_all_task_worktrees(force=force)
    console.print(f"[bold green]✓ Cleaned {cleaned} active task worktree(s). Pruned stale worktree references.[/bold green]")


# Aliases for hyphenated subcommands
cli.add_command(worktrees_list, name="worktrees-list")
cli.add_command(worktrees_clean, name="worktrees-clean")


def main():
    cli()


if __name__ == "__main__":
    main()
