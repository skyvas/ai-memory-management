"""Run autonomous development self-critique loop based on the Unified Memory & Dreaming architecture."""
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.dev_engine.memory_manager import MemoryManager, MemoryType
from src.dev_engine.dev_agents import ResearchAgent, CodingAgent, PlanningAgent
from src.dev_engine.dream_consolidation import DreamOrchestrator

console = Console()


def run_critique_cycle(agents_dir: str = ".agents"):
    console.print(Panel.fit(
        "[bold cyan]DataSec DB // Unified Multi-Agent Memory & Dreaming System[/bold cyan]\n"
        f"[dim]Git-Native File-Based Memory System: `{agents_dir}/` (Slide 1: Dreaming Pass & Slide 2: Unified Memory)[/dim]"
    ))

    memory_manager = MemoryManager(base_dir=agents_dir)

    # 1. WAKING MODE: Agents analyze and benchmark across sessions
    console.print("\n[bold yellow]═══ STEP 1: WAKING MODE (Real-Time Updates as Agents Work) ═══[/bold yellow]")
    
    research_agent = ResearchAgent(memory_manager, default_session_id="sess_01")
    coding_agent = CodingAgent(memory_manager, default_session_id="sess_02")
    planning_agent = PlanningAgent(memory_manager, default_session_id="sess_03")

    with console.status("[cyan]Agent A (sess_01) analyzing vulnerability specifications...[/cyan]"):
        res_out = research_agent.run("Research standards for PII and injection", {})
    console.print(f" [green]✔[/green] [bold]Agent A [sess_01][/bold]: {res_out['summary']}")

    with console.status("[cyan]Agent B (sess_02) benchmarking scanner against SQL and MongoDB test suites...[/cyan]"):
        code_out = coding_agent.run("Benchmark scanner on test samples", {
            "sql_sample": "samples/vulnerable_store.sql",
            "mongo_sample": "samples/mongo_users.json"
        })
    console.print(f" [green]✔[/green] [bold]Agent B [sess_02][/bold]: Executed {code_out['benchmarks_run']} benchmarks; logged scanner critiques into memory.")

    with console.status("[cyan]Agent C (sess_03) evaluating roadmap & updating team-memory/deploy.md...[/cyan]"):
        plan_out = planning_agent.run("Review milestone status", {})
    console.print(f" [green]✔[/green] [bold]Agent C [sess_03][/bold]: {plan_out['active_milestone']} -> updated `team_memory/deploy.md` in real-time.")

    # Display Active Episodic Memories by Session
    transcripts = memory_manager.get_session_transcripts()
    table = Table(title="Waking Experience Admitted to Episodic Memory by Session", header_style="bold magenta")
    table.add_column("Session ID", style="bold yellow", width=12)
    table.add_column("Memory ID", style="dim", width=14)
    table.add_column("Source Agent", style="cyan", width=16)
    table.add_column("Critique / Content", style="white")
    table.add_column("Confidence", justify="right", style="green", width=12)

    for sess_id, recs in transcripts.items():
        for m in recs[-2:]:  # show recent per session
            table.add_row(sess_id, m.get("id", ""), m.get("source", ""), m.get("content", "")[:80] + "...", f"{m.get('confidence', 0.9):.2f}")
    console.print(table)

    # 2. DREAMING MODE: Offline consolidation with Map-Reduce and Staging Isolation
    console.print("\n[bold yellow]═══ STEP 2: DREAMING MODE (Periodic Batch Updates: Verify, Organize, Enrich) ═══[/bold yellow]")
    console.print(" [dim]Pipeline: 1. Clone $MEM -> $MEM_OUT | 2. Map Subagents per Session | 3. Reduce (Verify, Organize, Enrich) | 4. Atomic Commit[/dim]")

    dreamer = DreamOrchestrator(memory_manager)
    with console.status("[magenta]Running dreaming cycle with staging isolation ($MEM_OUT)...[/magenta]"):
        dream_out = dreamer.run_dream_cycle(use_staging=True)

    console.print(f" [green]✔[/green] [bold]1. Staging Isolation ($MEM_OUT):[/bold] Snapshot contained {dream_out['snapshot_records_count']} memories.")
    console.print(f" [green]✔[/green] [bold]2. Map Phase:[/bold] Spawned {dream_out['sessions_count']} subagents across sessions: {', '.join(dream_out['sessions_processed'])}.")
    console.print(f" [green]✔[/green] [bold]3. Reduce Phase (Verify, Organize, Enrich):[/bold] {dream_out['proposals_count']} proposals generated, {dream_out['approved_proposals_count']} verified & approved.")
    
    new_ver = dream_out["new_version"]
    console.print(f" [green]✔[/green] [bold cyan]4. Atomic Commit Promoted to Memory Version {new_ver['version_number']}[/bold cyan] ({new_ver['change_summary']})")

    # Display Consolidated Topic Documents in team_memory/
    topic_docs = memory_manager.list_topic_docs()
    topic_table = Table(title=f"Shared Team Memory Documents (`team_memory/*.md` @ Version {new_ver['version_number']})", header_style="bold cyan")
    topic_table.add_column("Topic File", style="yellow", width=22)
    topic_table.add_column("Document Content Snippet", style="bright_white")

    for file_name, doc_content in sorted(topic_docs.items()):
        first_line = [line for line in doc_content.splitlines() if line.strip() and not line.startswith("#")]
        snippet = first_line[0][:100] + "..." if first_line else "Empty document"
        topic_table.add_row(file_name, snippet)
    console.print(topic_table)

    sem_files = list(memory_manager.semantic_dir.glob("*.md"))
    console.print(f"\n [bold green]✔[/bold green] [bold]Storage Synchronized:[/bold] {len(topic_docs)} team-memory docs in `{memory_manager.team_memory_dir}/`, {len(sem_files)} semantic records in `{memory_manager.semantic_dir}/`, audit versions in `{memory_manager.versions_file}`.")

    console.print(Panel("[bold green]Success:[/bold green] The Unified Memory & Dreaming System successfully synchronized real-time agent sessions, isolated the dreaming pass in staging ($MEM_OUT), verified and enriched knowledge, and promoted durable topic documents."))
    return dream_out


if __name__ == "__main__":
    run_critique_cycle()
