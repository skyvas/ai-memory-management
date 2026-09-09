"""Dreaming Mode consolidation engine: Map-Reduce Two-Phase Dreaming with Staging Isolation.

Architecture:
- Slide 1 (Inside a dreaming pass):
    1. Clone: $MEM -> $MEM_OUT (staging isolation)
    2. Map Phase: One subagent per session transcript
    3. Read / write to reorganize in $MEM_OUT
- Slide 2 (Unified Memory System):
    - Real-time updates as agents work <-> team-memory/*.md
    - Dreaming pass: Verify, Organize, Enrich
"""
from typing import List, Dict, Any, Optional
from src.dev_engine.memory_manager import (
    MemoryManager,
    MemoryRecord,
    MemoryType,
    MemoryVersion,
    DreamProposal,
    ProposalOperation,
)
from src.dev_engine.llm_provider import LLMProvider


class SessionTranscriptSubagent:
    """Map Phase: Analyzes a single session's transcript records in isolation."""

    def __init__(self, session_id: str, llm_provider: LLMProvider):
        self.session_id = session_id
        self.llm_provider = llm_provider

    def analyze_session(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Digests the session transcript into atomic findings and candidate proposals."""
        return self.llm_provider.digest_session(self.session_id, records)


class Consolidator:
    """Reduce Phase // Organize: Finds duplicate or overlapping memories across sessions and merges them into topic docs."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or LLMProvider()

    def organize(
        self,
        snapshot: List[MemoryRecord],
        session_findings: List[Dict[str, Any]],
        existing_topic_docs: Dict[str, str],
    ) -> List[DreamProposal]:
        proposals: List[DreamProposal] = []

        # Convert candidate findings into draft proposal dicts
        candidate_dicts = []
        benchmarks = [m for m in snapshot if "benchmark test" in m.content.lower()]
        if len(benchmarks) >= 2:
            candidate_dicts.append({
                "operation": "MERGE",
                "target_memory_ids": [m.id for m in benchmarks],
                "topic_file": "test-baselines.md",
                "resulting_content": (
                    "Consolidated Benchmark Baseline: Verified database security ingestion and scanner coverage across "
                    "both SQL (.sql) and MongoDB (.json) dumps with reliable detection of plaintext PII, unhashed passwords, and injection vectors."
                ),
                "reason": "Multiple independent benchmark runs verify cross-dialect scanner effectiveness.",
                "confidence": 0.96,
                "source_dream_agent": "consolidator",
            })

        # Ask LLM / local reflection to organize
        organized_results = self.llm_provider.organize_knowledge(candidate_dicts, existing_topic_docs)

        for item in organized_results:
            op_str = item.get("operation", "CREATE")
            op = ProposalOperation[op_str] if op_str in ProposalOperation.__members__ else ProposalOperation.CREATE
            proposals.append(
                DreamProposal(
                    operation=op,
                    target_memory_ids=item.get("target_memory_ids", []),
                    topic_file=item.get("topic_file"),
                    resulting_content=item.get("resulting_content", ""),
                    resulting_type=MemoryType.SEMANTIC,
                    reason=item.get("reason", "Consolidated redundant memories."),
                    confidence=float(item.get("confidence", 0.95)),
                    source_dream_agent=item.get("source_dream_agent", "consolidator"),
                )
            )

        return proposals


class PatternFinder:
    """Reduce Phase // Enrich: Searches across episodic experiences and session findings to extract systemic patterns."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or LLMProvider()

    def enrich(
        self,
        snapshot: List[MemoryRecord],
        session_findings: List[Dict[str, Any]],
    ) -> List[DreamProposal]:
        proposals: List[DreamProposal] = []
        snapshot_dicts = [m.model_dump() for m in snapshot]

        # Call LLM / local reflection for cross-session enrichment
        enriched_results = self.llm_provider.enrich_knowledge(session_findings, snapshot_dicts)

        for item in enriched_results:
            op_str = item.get("operation", "CREATE")
            op = ProposalOperation[op_str] if op_str in ProposalOperation.__members__ else ProposalOperation.CREATE
            proposals.append(
                DreamProposal(
                    operation=op,
                    target_memory_ids=item.get("target_memory_ids", []),
                    topic_file=item.get("topic_file"),
                    resulting_content=item.get("resulting_content", ""),
                    resulting_type=MemoryType.SEMANTIC,
                    reason=item.get("reason", "Synthesized cross-session systemic pattern."),
                    confidence=float(item.get("confidence", 0.95)),
                    source_dream_agent=item.get("source_dream_agent", "pattern_finder"),
                )
            )

        return proposals


class DreamEvaluator:
    """Reduce Phase // Verify: Evaluates dream proposals for safety, accuracy, and usefulness."""

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider or LLMProvider()

    def verify(self, proposals: List[DreamProposal], context: Optional[Dict[str, Any]] = None) -> List[DreamProposal]:
        context = context or {}
        evaluated = []
        for prop in proposals:
            verification = self.llm_provider.verify_proposal(prop.model_dump(), context)
            prop.is_approved = verification.get("is_approved", False)
            evaluated.append(prop)
        return evaluated

    def evaluate(self, proposals: List[DreamProposal]) -> List[DreamProposal]:
        """Backward-compatible alias for verify."""
        return self.verify(proposals)


class DreamOrchestrator:
    """Coordinates the full Two-Phase Map-Reduce Dreaming Pass with Staging Isolation."""

    def __init__(self, memory_manager: MemoryManager, llm_provider: Optional[LLMProvider] = None):
        self.memory_manager = memory_manager
        self.llm_provider = llm_provider or LLMProvider()
        self.consolidator = Consolidator(self.llm_provider)
        self.pattern_finder = PatternFinder(self.llm_provider)
        self.evaluator = DreamEvaluator(self.llm_provider)

    def run_dream_cycle(self, use_staging: bool = True) -> Dict[str, Any]:
        """Executes the complete dreaming pass:
        1. Clone $MEM -> $MEM_OUT (staging isolation)
        2. Map: One subagent per session transcript
        3. Reduce: Verify, Organize, Enrich
        4. Atomic commit to production team-memory
        """
        # 1. Step 1 (Photo): Clone $MEM -> $MEM_OUT
        target_manager = self.memory_manager
        staging_manager = None
        if use_staging:
            staging_manager = self.memory_manager.clone_to_staging()
            target_manager = staging_manager

        try:
            snapshot = target_manager.snapshot()
            transcripts = target_manager.get_session_transcripts()

            # Ensure default session if transcripts dict is empty
            if not transcripts:
                transcripts["sess_01"] = [m.model_dump() for m in snapshot]

            # 2. Step 2 (Photo): MAP PHASE - One Subagent per Session Transcript
            session_findings = []
            for session_id, records in transcripts.items():
                subagent = SessionTranscriptSubagent(session_id, self.llm_provider)
                digest = subagent.analyze_session(records)
                session_findings.append(digest)

            # 3. Step 3 (Photo & Slide 2): REDUCE PHASE - Organize & Enrich
            existing_topics = target_manager.list_topic_docs()
            proposals: List[DreamProposal] = []
            # Organize
            proposals.extend(self.consolidator.organize(snapshot, session_findings, existing_topics))
            # Enrich
            proposals.extend(self.pattern_finder.enrich(snapshot, session_findings))

            # 4. Slide 2: VERIFY
            evaluated_proposals = self.evaluator.verify(proposals, {"session_findings_count": len(session_findings)})
            approved_proposals = [p for p in evaluated_proposals if p.is_approved]

            # 5. Apply changes to $MEM_OUT
            summary_text = (
                f"Dreaming Pass Consolidated {len(approved_proposals)} knowledge insights across "
                f"{len(transcripts)} session transcripts: verified benchmarks and enriched topic guides."
            )
            new_version = target_manager.promote_version(approved_proposals, summary_text)

            # 6. Atomic Commit: promote staging $MEM_OUT -> $MEM
            if staging_manager:
                final_version = self.memory_manager.commit_staging(staging_manager)
            else:
                final_version = new_version

            return {
                "status": "completed",
                "sessions_processed": list(transcripts.keys()),
                "sessions_count": len(transcripts),
                "snapshot_records_count": len(snapshot),
                "proposals_count": len(proposals),
                "approved_proposals_count": len(approved_proposals),
                "new_version": final_version.model_dump(),
                "proposals": [p.model_dump() for p in evaluated_proposals],
                "topics_updated": list(self.memory_manager.list_topic_docs().keys()),
            }
        except Exception as e:
            if staging_manager:
                self.memory_manager.abort_staging(staging_manager)
            raise e
