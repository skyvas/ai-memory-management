"""Memory Manager implementing the Git-native .agents/ file-based memory architecture."""
import os
import json
import uuid
import datetime
from pathlib import Path
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROJECT_STATE = "project_state"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    TASK = "task"
    AGENT = "agent"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemoryRecord(BaseModel):
    id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:8]}")
    type: MemoryType = MemoryType.EPISODIC
    content: str
    scope: MemoryScope = MemoryScope.PROJECT
    project_id: str = "dbsec_v1"
    importance: float = 0.8
    confidence: float = 0.95
    source: str = "agent"
    status: MemoryStatus = MemoryStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")


class ProposalOperation(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    MERGE = "MERGE"
    ARCHIVE = "ARCHIVE"
    DELETE = "DELETE"


class DreamProposal(BaseModel):
    id: str = Field(default_factory=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    operation: ProposalOperation
    target_memory_ids: List[str] = Field(default_factory=list)
    resulting_content: str
    resulting_type: MemoryType = MemoryType.SEMANTIC
    reason: str
    confidence: float = 0.9
    source_dream_agent: str = "consolidator"
    is_approved: Optional[bool] = None


class MemoryVersion(BaseModel):
    version_number: int
    created_at: str
    promoted_proposals_count: int
    active_records_count: int
    change_summary: str


class MemoryManager:
    """Manages multi-agent memory using a Git-native .agents/ directory structure.
    
    Structure:
      .agents/
        ├── project_state.json       (Shared project state & active constraints)
        ├── versions.json            (Memory version registry & audit history)
        ├── semantic/                (Human-readable Markdown semantic memories)
        │   ├── {mem_id}.md
        │   └── archive/
        ├── episodic/                (Append-only JSONL episodic event logs)
        │   ├── episodic_log.jsonl
        │   └── archive/
        └── working/                 (Ephemeral session scratchpads)
    """

    def __init__(self, base_dir: Union[str, Path] = ".agents", db_path: Optional[str] = None):
        if db_path:
            p = Path(db_path)
            if p.suffix in (".db", ".sqlite", ".sqlite3"):
                self.base_dir = p.parent / f"{p.stem}_agents"
            else:
                self.base_dir = p
        else:
            self.base_dir = Path(base_dir)

        self.semantic_dir = self.base_dir / "semantic"
        self.semantic_archive_dir = self.semantic_dir / "archive"
        self.episodic_dir = self.base_dir / "episodic"
        self.episodic_archive_dir = self.episodic_dir / "archive"
        self.working_dir = self.base_dir / "working"
        self.project_state_file = self.base_dir / "project_state.json"
        self.versions_file = self.base_dir / "versions.json"

        self._current_version = 1
        self._init_storage()

    def _init_storage(self):
        """Initializes the directory structure and baseline manifests."""
        self.semantic_dir.mkdir(parents=True, exist_ok=True)
        self.semantic_archive_dir.mkdir(parents=True, exist_ok=True)
        self.episodic_dir.mkdir(parents=True, exist_ok=True)
        self.episodic_archive_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        if not self.versions_file.exists():
            initial_version = MemoryVersion(
                version_number=1,
                created_at=datetime.datetime.utcnow().isoformat() + "Z",
                promoted_proposals_count=0,
                active_records_count=0,
                change_summary="Initial Memory Baseline",
            )
            self._write_versions([initial_version])
            self._current_version = 1
        else:
            versions = self.get_versions()
            if versions:
                self._current_version = max(v.version_number for v in versions)
            else:
                self._current_version = 1

        if not self.project_state_file.exists():
            self._write_project_state([])

    def remember(self, record: MemoryRecord) -> Optional[MemoryRecord]:
        """Admission pipeline: filter out low importance or trivial memories."""
        if record.importance < 0.2:
            return None  # Filtered out by admission policy

        # Set active version
        record.version = self._current_version

        if record.type == MemoryType.SEMANTIC:
            self._write_semantic_record(record)
        elif record.type == MemoryType.PROJECT_STATE:
            states = self._read_project_state()
            # Replace existing if same id, else append
            states = [s for s in states if s.id != record.id]
            states.append(record)
            self._write_project_state(states)
        elif record.type == MemoryType.WORKING:
            target_path = self.working_dir / f"{record.id}.json"
            target_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        else:  # EPISODIC
            log_file = self.episodic_dir / "episodic_log.jsonl"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(record.model_dump_json() + "\n")

        return record

    def recall(
        self,
        query: Optional[str] = None,
        mem_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        """Hybrid search combining scope, type filters, and keyword relevance across .agents/ storage."""
        records: List[MemoryRecord] = []

        # 1. Semantic records from .agents/semantic/*.md
        if mem_type is None or mem_type == MemoryType.SEMANTIC:
            for p in self.semantic_dir.glob("*.md"):
                if p.is_file():
                    rec = self._parse_markdown_record(p)
                    if rec and rec.status == MemoryStatus.ACTIVE:
                        records.append(rec)

        # 2. Project state records from .agents/project_state.json
        if mem_type is None or mem_type == MemoryType.PROJECT_STATE:
            for s in self._read_project_state():
                if s.status == MemoryStatus.ACTIVE:
                    records.append(s)

        # 3. Episodic records from .agents/episodic/episodic_log.jsonl
        if mem_type is None or mem_type == MemoryType.EPISODIC:
            log_file = self.episodic_dir / "episodic_log.jsonl"
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            rec = MemoryRecord(**data)
                            if rec.status == MemoryStatus.ACTIVE:
                                records.append(rec)
                        except Exception:
                            continue

        # 4. Working records from .agents/working/*.json
        if mem_type == MemoryType.WORKING:
            for p in self.working_dir.glob("*.json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    rec = MemoryRecord(**data)
                    if rec.status == MemoryStatus.ACTIVE:
                        records.append(rec)
                except Exception:
                    continue

        # Filter by mem_type if specified
        if mem_type:
            records = [r for r in records if r.type == mem_type]

        # Filter by scope if specified
        if scope:
            records = [r for r in records if r.scope == scope]

        # Sort by importance and created_at descending as baseline
        records.sort(key=lambda r: (r.importance, r.created_at), reverse=True)

        # In-memory keyword filtering and re-ranking if query provided
        if query:
            q_terms = set(query.lower().split())
            matching = [r for r in records if any(term in r.content.lower() for term in q_terms)]
            if matching:
                records = matching

            def score(rec: MemoryRecord) -> float:
                content_lower = rec.content.lower()
                matches = sum(1 for term in q_terms if term in content_lower)
                return rec.importance + (matches * 0.5)

            records.sort(key=score, reverse=True)

        return records[:limit]

    def snapshot(self) -> List[MemoryRecord]:
        """Creates an isolated copy of current active memory for dreaming."""
        return self.recall(limit=1000)

    def archive(self, memory_id: str) -> bool:
        """Archives a memory record by moving it to the archive folder or updating its status."""
        # Check semantic
        sem_file = self.semantic_dir / f"{memory_id}.md"
        if sem_file.exists():
            rec = self._parse_markdown_record(sem_file)
            if rec:
                rec.status = MemoryStatus.ARCHIVED
                self._write_markdown_record(self.semantic_archive_dir / f"{memory_id}.md", rec)
                sem_file.unlink()
                return True

        # Check project state
        states = self._read_project_state()
        found_state = False
        new_states = []
        for s in states:
            if s.id == memory_id:
                s.status = MemoryStatus.ARCHIVED
                found_state = True
            new_states.append(s)
        if found_state:
            self._write_project_state(new_states)
            return True

        # Check episodic
        log_file = self.episodic_dir / "episodic_log.jsonl"
        if log_file.exists():
            lines = []
            archived_rec = None
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    try:
                        data = json.loads(line_str)
                        if data.get("id") == memory_id:
                            data["status"] = MemoryStatus.ARCHIVED.value
                            archived_rec = data
                            continue
                        lines.append(line_str)
                    except Exception:
                        lines.append(line_str)

            if archived_rec:
                # Rewrite episodic log without archived record
                with open(log_file, "w", encoding="utf-8") as f:
                    for l in lines:
                        f.write(l + "\n")
                # Append to archive log
                archive_log = self.episodic_archive_dir / "archived_log.jsonl"
                with open(archive_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(archived_rec) + "\n")
                return True

        # Check working
        work_file = self.working_dir / f"{memory_id}.json"
        if work_file.exists():
            work_file.unlink()
            return True

        return False

    def promote_version(self, proposals: List[DreamProposal], summary: str) -> MemoryVersion:
        """Applies evaluated dream proposals and bumps the memory version."""
        new_version_num = self._current_version + 1

        for prop in proposals:
            if not prop.is_approved:
                continue

            if prop.operation == ProposalOperation.MERGE:
                # Archive target memories
                for t_id in prop.target_memory_ids:
                    self.archive(t_id)

                # Create consolidated semantic memory
                new_mem = MemoryRecord(
                    type=prop.resulting_type,
                    content=prop.resulting_content,
                    scope=MemoryScope.PROJECT,
                    importance=0.9,
                    confidence=prop.confidence,
                    source=prop.source_dream_agent,
                    metadata={"merged_from": prop.target_memory_ids, "reason": prop.reason},
                    version=new_version_num,
                )
                self._write_semantic_record(new_mem)

            elif prop.operation == ProposalOperation.CREATE:
                new_mem = MemoryRecord(
                    type=prop.resulting_type,
                    content=prop.resulting_content,
                    scope=MemoryScope.PROJECT,
                    importance=0.85,
                    confidence=prop.confidence,
                    source=prop.source_dream_agent,
                    metadata={"reason": prop.reason},
                    version=new_version_num,
                )
                self._write_semantic_record(new_mem)

        # Calculate active records count
        active_count = len(self.recall(limit=10000))
        approved_count = sum(1 for p in proposals if p.is_approved)

        ver = MemoryVersion(
            version_number=new_version_num,
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
            promoted_proposals_count=approved_count,
            active_records_count=active_count,
            change_summary=summary,
        )

        versions = self.get_versions()
        versions.append(ver)
        self._write_versions(versions)

        self._current_version = new_version_num
        return ver

    def get_versions(self) -> List[MemoryVersion]:
        """Returns the list of recorded memory versions."""
        if not self.versions_file.exists():
            return []
        try:
            data = json.loads(self.versions_file.read_text(encoding="utf-8"))
            return [MemoryVersion(**v) for v in data]
        except Exception:
            return []

    def clear(self):
        """Clears all stored memories and resets to version 1 baseline."""
        # Clear semantic
        for f in self.semantic_dir.glob("*.md"):
            try:
                f.unlink()
            except Exception:
                pass
        for f in self.semantic_archive_dir.glob("*.md"):
            try:
                f.unlink()
            except Exception:
                pass

        # Clear episodic
        log_file = self.episodic_dir / "episodic_log.jsonl"
        if log_file.exists():
            log_file.unlink()
        archive_log = self.episodic_archive_dir / "archived_log.jsonl"
        if archive_log.exists():
            archive_log.unlink()

        # Clear working
        for f in self.working_dir.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass

        # Reset project state
        self._write_project_state([])

        # Reset versions
        baseline = MemoryVersion(
            version_number=1,
            created_at=datetime.datetime.utcnow().isoformat() + "Z",
            promoted_proposals_count=0,
            active_records_count=0,
            change_summary="Reset Memory Baseline",
        )
        self._write_versions([baseline])
        self._current_version = 1

    # --- Internal Storage Helpers ---

    def _write_semantic_record(self, record: MemoryRecord):
        target_file = self.semantic_dir / f"{record.id}.md"
        self._write_markdown_record(target_file, record)

    def _write_markdown_record(self, file_path: Path, record: MemoryRecord):
        first_line = record.content.strip().split("\n")[0]
        title = first_line[:80].replace("#", "").strip()
        if len(first_line) > 80:
            title += "..."

        frontmatter = [
            "---",
            f"id: {record.id}",
            f"type: {record.type.value}",
            f"scope: {record.scope.value}",
            f"project_id: {record.project_id}",
            f"importance: {record.importance}",
            f"confidence: {record.confidence}",
            f"source: {record.source}",
            f"status: {record.status.value}",
            f"version: {record.version}",
            f"created_at: {record.created_at}",
            f"metadata: {json.dumps(record.metadata)}",
            "---",
            "",
            f"# {title}",
            "",
            record.content.strip(),
            "",
        ]

        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = file_path.with_suffix(".tmp")
        tmp_file.write_text("\n".join(frontmatter), encoding="utf-8")
        tmp_file.replace(file_path)

    def _parse_markdown_record(self, file_path: Path) -> Optional[MemoryRecord]:
        try:
            text = file_path.read_text(encoding="utf-8")
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    frontmatter_str = parts[1]
                    body = parts[2].strip()

                    meta_dict: Dict[str, str] = {}
                    for line in frontmatter_str.strip().splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta_dict[k.strip()] = v.strip()

                    metadata_raw = meta_dict.get("metadata", "{}")
                    try:
                        custom_metadata = json.loads(metadata_raw)
                    except Exception:
                        custom_metadata = {}

                    content = body
                    lines = body.splitlines()
                    if lines and lines[0].startswith("# "):
                        content = "\n".join(lines[1:]).strip()
                    if not content:
                        content = body

                    return MemoryRecord(
                        id=meta_dict.get("id", file_path.stem),
                        type=MemoryType(meta_dict.get("type", "semantic")),
                        content=content,
                        scope=MemoryScope(meta_dict.get("scope", "project")),
                        project_id=meta_dict.get("project_id", "dbsec_v1"),
                        importance=float(meta_dict.get("importance", 0.9)),
                        confidence=float(meta_dict.get("confidence", 0.95)),
                        source=meta_dict.get("source", "consolidator"),
                        status=MemoryStatus(meta_dict.get("status", "active")),
                        metadata=custom_metadata,
                        version=int(meta_dict.get("version", 1)),
                        created_at=meta_dict.get("created_at", datetime.datetime.utcnow().isoformat() + "Z"),
                    )
        except Exception:
            return None
        return None

    def _read_project_state(self) -> List[MemoryRecord]:
        if not self.project_state_file.exists():
            return []
        try:
            data = json.loads(self.project_state_file.read_text(encoding="utf-8"))
            return [MemoryRecord(**item) for item in data]
        except Exception:
            return []

    def _write_project_state(self, records: List[MemoryRecord]):
        data = [r.model_dump() for r in records]
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self.project_state_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.replace(self.project_state_file)

    def _write_versions(self, versions: List[MemoryVersion]):
        data = [v.model_dump() for v in versions]
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self.versions_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_file.replace(self.versions_file)
