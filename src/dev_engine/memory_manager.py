"""Memory Manager implementing the Dreaming Multi-Agent Memory System from README.md."""
import sqlite3
import json
import uuid
import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
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
    """Manages multi-agent memory with SQLite persistence, admission filtering, and snapshotting."""

    def __init__(self, db_path: str = "dev_memory.db"):
        self.db_path = db_path
        self._current_version = 1
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    content TEXT,
                    scope TEXT,
                    project_id TEXT,
                    importance REAL,
                    confidence REAL,
                    source TEXT,
                    status TEXT,
                    metadata TEXT,
                    version INTEGER,
                    created_at TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS versions (
                    version_number INTEGER PRIMARY KEY,
                    created_at TEXT,
                    promoted_proposals_count INTEGER,
                    active_records_count INTEGER,
                    change_summary TEXT
                )
                """
            )
            # Check latest version
            cursor.execute("SELECT MAX(version_number) FROM versions")
            row = cursor.fetchone()
            if row and row[0]:
                self._current_version = row[0]
            else:
                cursor.execute(
                    "INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                    (1, datetime.datetime.utcnow().isoformat() + "Z", 0, 0, "Initial Memory Baseline"),
                )
                conn.commit()

    def remember(self, record: MemoryRecord) -> Optional[MemoryRecord]:
        """Admission pipeline: filter out low importance or trivial memories."""
        if record.importance < 0.2:
            return None  # Filtered out by admission policy

        # Set active version
        record.version = self._current_version

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO memories 
                (id, type, content, scope, project_id, importance, confidence, source, status, metadata, version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.type.value,
                    record.content,
                    record.scope.value,
                    record.project_id,
                    record.importance,
                    record.confidence,
                    record.source,
                    record.status.value,
                    json.dumps(record.metadata),
                    record.version,
                    record.created_at,
                ),
            )
            conn.commit()
        return record

    def recall(
        self,
        query: Optional[str] = None,
        mem_type: Optional[MemoryType] = None,
        scope: Optional[MemoryScope] = None,
        limit: int = 20,
    ) -> List[MemoryRecord]:
        """Hybrid search combining scope, type filters, and keyword relevance."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            sql = "SELECT id, type, content, scope, project_id, importance, confidence, source, status, metadata, version, created_at FROM memories WHERE status = 'active'"
            params: List[Any] = []

            if mem_type:
                sql += " AND type = ?"
                params.append(mem_type.value)
            if scope:
                sql += " AND scope = ?"
                params.append(scope.value)

            sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit * 2)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        records = [self._row_to_record(r) for r in rows]

        # In-memory keyword re-ranking if query provided
        if query:
            q_terms = set(query.lower().split())
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
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET status = 'archived' WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def promote_version(self, proposals: List[DreamProposal], summary: str) -> MemoryVersion:
        """Applies evaluated dream proposals and bumps the memory version."""
        new_version_num = self._current_version + 1

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for prop in proposals:
                if not prop.is_approved:
                    continue

                if prop.operation == ProposalOperation.MERGE:
                    # Archive targets
                    for t_id in prop.target_memory_ids:
                        cursor.execute("UPDATE memories SET status = 'archived' WHERE id = ?", (t_id,))
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
                    cursor.execute(
                        """
                        INSERT INTO memories (id, type, content, scope, project_id, importance, confidence, source, status, metadata, version, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_mem.id,
                            new_mem.type.value,
                            new_mem.content,
                            new_mem.scope.value,
                            new_mem.project_id,
                            new_mem.importance,
                            new_mem.confidence,
                            new_mem.source,
                            new_mem.status.value,
                            json.dumps(new_mem.metadata),
                            new_version_num,
                            new_mem.created_at,
                        ),
                    )
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
                    cursor.execute(
                        """
                        INSERT INTO memories (id, type, content, scope, project_id, importance, confidence, source, status, metadata, version, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            new_mem.id,
                            new_mem.type.value,
                            new_mem.content,
                            new_mem.scope.value,
                            new_mem.project_id,
                            new_mem.importance,
                            new_mem.confidence,
                            new_mem.source,
                            new_mem.status.value,
                            json.dumps(new_mem.metadata),
                            new_version_num,
                            new_mem.created_at,
                        ),
                    )

            # Count active records
            cursor.execute("SELECT COUNT(*) FROM memories WHERE status = 'active'")
            active_count = cursor.fetchone()[0]

            approved_count = sum(1 for p in proposals if p.is_approved)
            ver = MemoryVersion(
                version_number=new_version_num,
                created_at=datetime.datetime.utcnow().isoformat() + "Z",
                promoted_proposals_count=approved_count,
                active_records_count=active_count,
                change_summary=summary,
            )

            cursor.execute(
                "INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                (ver.version_number, ver.created_at, ver.promoted_proposals_count, ver.active_records_count, ver.change_summary),
            )
            conn.commit()

        self._current_version = new_version_num
        return ver

    def get_versions(self) -> List[MemoryVersion]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version_number, created_at, promoted_proposals_count, active_records_count, change_summary FROM versions ORDER BY version_number ASC")
            rows = cursor.fetchall()
            return [
                MemoryVersion(
                    version_number=r[0],
                    created_at=r[1],
                    promoted_proposals_count=r[2],
                    active_records_count=r[3],
                    change_summary=r[4],
                )
                for r in rows
            ]

    def clear(self):
        """Clears all stored memories and resets to version 1 baseline."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories")
            cursor.execute("DELETE FROM versions")
            cursor.execute(
                "INSERT INTO versions VALUES (?, ?, ?, ?, ?)",
                (1, datetime.datetime.utcnow().isoformat() + "Z", 0, 0, "Reset Memory Baseline"),
            )
            conn.commit()
        self._current_version = 1

    def _row_to_record(self, row: tuple) -> MemoryRecord:
        return MemoryRecord(
            id=row[0],
            type=MemoryType(row[1]),
            content=row[2],
            scope=MemoryScope(row[3]),
            project_id=row[4],
            importance=row[5],
            confidence=row[6],
            source=row[7],
            status=MemoryStatus(row[8]),
            metadata=json.loads(row[9]) if row[9] else {},
            version=row[10],
            created_at=row[11],
        )
