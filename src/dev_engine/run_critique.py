"""Run autonomous development self-critique loop based on README.md."""
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.dev_engine.memory_manager import MemoryManager, MemoryType
from src.dev_engine.dev_agents import ResearchAgent, CodingAgent, PlanningAgent
from src.dev_engine.dream_consolidation import DreamOrchestrator

console = Console()


def run_critique_cycle(db_path: str = "dev_memory.db"):
    console.print(Panel.fit("[bold cyan]DataSec DB // Multi-Agent Development & Self-Critique Engine[/bold cyan]\n[dim]Architecture grounded in Dreaming Multi-Agent Memory System (README.md)[/dim]"))

    memory_manager = MemoryManager(db_path=db_path)

    # 1. WAKING MODE: Agents analyze and benchmark
    console.print("\n[bold yellow]═══ STEP 1: WAKING MODE (Agents Generate Experience) ═══[/bold yellow]")
    
    research_agent = ResearchAgent(memory_manager)
    coding_agent = CodingAgent(memory_manager)
    planning_agent = PlanningAgent(memory_manager)

    with console.status("[cyan]Research Agent analyzing vulnerability specifications...[/cyan]"):
        res_out = research_agent.run("Research standards for PII and injection", {})
    console.print(f" [green]✔[/green] [bold]Research Agent[/bold]: {res_out['summary']}")

    with console.status("[cyan]Coding Agent benchmarking scanner against SQL and MongoDB test suites...[/cyan]"):
        code_out = coding_agent.run("Benchmark scanner on test samples", {
            "sql_sample": "samples/vulnerable_store.sql",
            "mongo_sample": "samples/mongo_users.json"
        })
    console.print(f" [green]✔[/green] [bold]Coding Agent[/bold]: Executed {code_out['benchmarks_run']} benchmarks; logged scanner critiques into memory.")

    with console.status("[cyan]Planning Agent evaluating roadmap milestones...[/cyan]"):
        plan_out = planning_agent.run("Review milestone status", {})
    console.print(f" [green]✔[/green] [bold]Planning Agent[/bold]: {plan_out['active_milestone']}")

    # Display Active Episodic Memories
    episodic_memories = memory_manager.recall(mem_type=MemoryType.EPISODIC, limit=10)
    table = Table(title="Waking Experience & Critiques Admitted to Memory", header_style="bold magenta")
    table.add_column("Memory ID", style="dim", width=12)
    table.add_column("Source Agent", style="cyan", width=16)
    table.add_column("Critique / Content", style="white")
    table.add_column("Confidence", justify="right", style="green", width=12)

    for m in episodic_memories:
        table.add_row(m.id, m.source, m.content[:90] + "...", f"{m.confidence:.2f}")
    console.print(table)

    # 2. DREAMING MODE: Offline consolidation on memory snapshot
    console.print("\n[bold yellow]═══ STEP 2: DREAMING MODE (Offline Memory Consolidation) ═══[/bold yellow]")
    dreamer = DreamOrchestrator(memory_manager)
    with console.status("[magenta]Running dreaming cycle: Consolidator, Pattern Finder, Evaluator...[/magenta]"):
        dream_out = dreamer.run_dream_cycle()

    console.print(f" [green]✔[/green] [bold]Dreaming Cycle Completed[/bold]: Snapshot contained {dream_out['snapshot_records_count']} memories.")
    console.print(f" [green]✔[/green] [bold]Proposals Evaluated[/bold]: {dream_out['proposals_count']} generated, {dream_out['approved_proposals_count']} approved.")
    
    new_ver = dream_out["new_version"]
    console.print(f" [green]✔[/green] [bold cyan]Promoted to Memory Version {new_ver['version_number']}[/bold cyan] ({new_ver['change_summary']})")

    # Display Consolidated Semantic Knowledge
    semantic_memories = memory_manager.recall(mem_type=MemoryType.SEMANTIC, limit=10)
    sem_table = Table(title=f"Consolidated Knowledge Base (Memory Version {new_ver['version_number']})", header_style="bold cyan")
    sem_table.add_column("ID", style="dim", width=12)
    sem_table.add_column("Type", style="yellow", width=10)
    sem_table.add_column("Consolidated Insight / Rule Improvement", style="bright_white")
    sem_table.add_column("Source", style="cyan", width=15)

    for sm in semantic_memories:
        sem_table.add_row(sm.id, sm.type.value, sm.content, sm.source)
    console.print(sem_table)

    console.print(Panel("[bold green]Success:[/bold green] The multi-agent development engine successfully self-criticized, evaluated the security tool, and consolidated findings into actionable durable knowledge."))
    return dream_out


if __name__ == "__main__":
    run_critique_cycle()
