"""One-time migration script: Migrates SQLite dev_memory.db records into .agents/ directory structure."""
import sqlite3
import json
import datetime
from pathlib import Path

def migrate():
    db_path = Path("dev_memory.db")
    if not db_path.exists():
        print("No dev_memory.db found. Skipping migration.")
        return

    agents_dir = Path(".agents")
    semantic_dir = agents_dir / "semantic"
    episodic_dir = agents_dir / "episodic"
    working_dir = agents_dir / "working"
    
    semantic_dir.mkdir(parents=True, exist_ok=True)
    episodic_dir.mkdir(parents=True, exist_ok=True)
    working_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 1. Migrate versions
    cursor.execute("SELECT version_number, created_at, promoted_proposals_count, active_records_count, change_summary FROM versions ORDER BY version_number ASC")
    version_rows = cursor.fetchall()
    versions = [
        {
            "version_number": r[0],
            "created_at": r[1],
            "promoted_proposals_count": r[2],
            "active_records_count": r[3],
            "change_summary": r[4],
        }
        for r in version_rows
    ]
    if not versions:
        versions = [{
            "version_number": 1,
            "created_at": datetime.datetime.utcnow().isoformat() + "Z",
            "promoted_proposals_count": 0,
            "active_records_count": 0,
            "change_summary": "Initial Memory Baseline",
        }]
    
    versions_file = agents_dir / "versions.json"
    versions_file.write_text(json.dumps(versions, indent=2), encoding="utf-8")
    print(f"Migrated {len(versions)} versions to {versions_file}")

    # 2. Migrate memories
    cursor.execute("SELECT id, type, content, scope, project_id, importance, confidence, source, status, metadata, version, created_at FROM memories")
    mem_rows = cursor.fetchall()
    print(f"Found {len(mem_rows)} memories in {db_path}")

    project_state_records = []
    episodic_records = []

    for r in mem_rows:
        rec = {
            "id": r[0],
            "type": r[1],
            "content": r[2],
            "scope": r[3],
            "project_id": r[4],
            "importance": r[5],
            "confidence": r[6],
            "source": r[7],
            "status": r[8],
            "metadata": json.loads(r[9]) if r[9] else {},
            "version": r[10],
            "created_at": r[11],
        }

        if rec["type"] == "semantic":
            title = rec["content"].split("\n")[0][:80]
            if len(rec["content"].split("\n")[0]) > 80:
                title += "..."
            title = title.replace("#", "").strip()

            md_content = f"""---
id: {rec['id']}
type: {rec['type']}
scope: {rec['scope']}
project_id: {rec['project_id']}
importance: {rec['importance']}
confidence: {rec['confidence']}
source: {rec['source']}
status: {rec['status']}
version: {rec['version']}
created_at: {rec['created_at']}
metadata: {json.dumps(rec['metadata'])}
---

# {title}

{rec['content']}
"""
            target_path = semantic_dir / f"{rec['id']}.md"
            target_path.write_text(md_content, encoding="utf-8")
        elif rec["type"] == "project_state":
            project_state_records.append(rec)
        else:
            episodic_records.append(rec)

    # Save project state
    project_state_file = agents_dir / "project_state.json"
    project_state_file.write_text(json.dumps(project_state_records, indent=2), encoding="utf-8")
    print(f"Migrated {len(project_state_records)} project state records to {project_state_file}")

    # Save episodic
    episodic_file = episodic_dir / "episodic_log.jsonl"
    with open(episodic_file, "w", encoding="utf-8") as f:
        for er in episodic_records:
            f.write(json.dumps(er) + "\n")
    print(f"Migrated {len(episodic_records)} episodic records to {episodic_file}")
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
