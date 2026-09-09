"""Memory and offline consolidation (dreaming) components for AgentGraph."""
from src.memory.markdown_memory import MarkdownMemoryManager, FailurePattern, ArchitectureInvariant, ADR
from src.memory.gemini_updater import GeminiUpdater
from src.memory.context_pruner import ContextPruner
from src.memory.dreaming_engine import DreamingEngine

__all__ = [
    "MarkdownMemoryManager",
    "FailurePattern",
    "ArchitectureInvariant",
    "ADR",
    "GeminiUpdater",
    "ContextPruner",
    "DreamingEngine"
]
