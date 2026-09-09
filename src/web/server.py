"""FastAPI Web Server for DataSec DB with native SQLite .db, SQL, and MongoDB auditing."""
import os
import asyncio
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.dbsec.models import (
    ScanSummary,
    VulnerabilityFinding,
    UserRole,
    UserProfile,
)
from src.dbsec.ingester_factory import get_ingester_for_file
from src.dbsec.scanner import VulnerabilityScanner
from src.dbsec.reporter import SecurityReporter

app = FastAPI(title="DataSec DB - Enterprise Database Security Auditor")

# In-memory session store & database state
SESSIONS: Dict[str, UserProfile] = {}
USERS = {
    "admin": {"password": "admin", "role": UserRole.ADMIN, "display_name": "Security Administrator"},
    "analyst": {"password": "analyst", "role": UserRole.ANALYST, "display_name": "Compliance Analyst"},
}

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
SAMPLE_DIR = Path("samples")

# State
APP_STATE: Dict[str, Any] = {
    "files": [],
    "findings": [],
    "total_records": 0,
    "total_tables_collections": 0,
    "risk_score": 0,
    "critical_count": 0,
    "high_count": 0,
    "medium_count": 0,
    "low_count": 0,
    "compliance_breakdown": {"PCI-DSS": 0, "GDPR": 0, "HIPAA": 0, "OWASP": 0},
    "last_scan_file": None,
    "last_scan_type": None,
    "current_activity": "System ready. Select or upload a SQLite (.db), SQL, or MongoDB file to audit.",
}

# Event broadcast queue for SSE
EVENT_QUEUES: List[asyncio.Queue] = []


def broadcast_event(event_type: str, data: Dict[str, Any]):
    msg = json.dumps({"type": event_type, "data": data})
    for q in list(EVENT_QUEUES):
        try:
            q.put_nowait(msg)
        except Exception:
            pass


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[UserProfile]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return SESSIONS.get(token)


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = USERS.get(req.username.strip().lower())
    if not user or user["password"] != req.password.strip():
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    
    token = f"sess_{uuid.uuid4().hex}"
    profile = UserProfile(
        username=req.username,
        role=user["role"],
        display_name=user["display_name"],
    )
    SESSIONS[token] = profile
    return {"token": token, "user": profile.model_dump()}


@app.get("/api/auth/me")
async def get_me(user: Optional[UserProfile] = Depends(get_current_user)):
    if not user:
        return {"authenticated": False}
    return {"authenticated": True, "user": user.model_dump()}


@app.post("/api/auth/logout")
async def logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        SESSIONS.pop(token, None)
    return {"status": "logged_out"}


@app.get("/api/samples")
async def get_samples():
    samples = [
        {
            "id": "vulnerable_enterprise.db",
            "name": "vulnerable_enterprise.db",
            "type": "SQLite DB",
            "size": "1.1 MB",
            "records": "10,500 rows",
            "description": "Enterprise-scale SQLite database with 10,500+ records. Includes plaintext credentials, MD5/SHA-1 hashes, Luhn-valid credit cards, SSNs, AWS/GitHub/Stripe keys, RSA private keys, missing primary keys, and insecure PRAGMA configurations.",
            "is_vulnerable": True,
        },
        {
            "id": "secure_store.db",
            "name": "secure_store.db",
            "type": "SQLite DB",
            "size": "116 KB",
            "records": "1,000 rows",
            "description": "Hardened SQLite database with salted Argon2id/bcrypt hashes, tokenized payment records, and secure_delete=ON PRAGMA.",
            "is_vulnerable": False,
        },
        {
            "id": "vulnerable_store.sql",
            "name": "vulnerable_store.sql",
            "type": "SQL Dump",
            "size": "1.2 KB",
            "records": "6 rows",
            "description": "E-commerce database dump containing plaintext credit cards, unhashed passwords, SQL injection, and GRANT ALL.",
            "is_vulnerable": True,
        },
        {
            "id": "mongo_users.json",
            "name": "mongo_users.json",
            "type": "MongoDB",
            "size": "0.8 KB",
            "records": "3 docs",
            "description": "MongoDB export containing plaintext SSNs, AWS secrets, and dangerous $where JavaScript execution query.",
            "is_vulnerable": True,
        },
        {
            "id": "secure_store.sql",
            "name": "secure_store.sql",
            "type": "SQL Dump",
            "size": "1.5 KB",
            "records": "5 rows",
            "description": "Hardened SQL database reference with salted bcrypt hashes, tokenized payments, and parameterized queries.",
            "is_vulnerable": False,
        },
        {
            "id": "clean_mongo.json",
            "name": "clean_mongo.json",
            "type": "MongoDB",
            "size": "0.5 KB",
            "records": "2 docs",
            "description": "Sanitized MongoDB catalog with no PII leaks and clean operator usage.",
            "is_vulnerable": False,
        },
    ]
    return samples


@app.get("/api/state")
async def get_state():
    return APP_STATE


@app.get("/api/stream")
async def sse_stream():
    queue = asyncio.Queue()
    EVENT_QUEUES.append(queue)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'connected', 'msg': 'Live SSE Stream connected'})}\n\n"
            while True:
                msg = await queue.get()
                yield f"data: {msg}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in EVENT_QUEUES:
                EVENT_QUEUES.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class ScanRequest(BaseModel):
    sample_id: Optional[str] = None
    file_path: Optional[str] = None


@app.post("/api/scan")
async def run_scan(req: ScanRequest):
    # Resolve file path
    target_path = None
    if req.sample_id:
        target_path = SAMPLE_DIR / req.sample_id
    elif req.file_path:
        target_path = Path(req.file_path)

    if not target_path or not target_path.exists():
        raise HTTPException(status_code=404, detail="Target database file not found.")

    file_name = target_path.name
    suffix = target_path.suffix.lower()

    if suffix not in (".db", ".sqlite", ".sqlite3", ".sql", ".json", ".jsonl"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported database format. Supported: .db, .sqlite, .sqlite3, .sql, .json, .jsonl",
        )

    broadcast_event("status", {"text": f"Ingesting database file `{file_name}`...", "progress": 0.05})
    await asyncio.sleep(0.05)

    try:
        ingester = get_ingester_for_file(str(target_path))
        parsed_db = ingester.ingest_file(str(target_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ingest database: {str(e)}")

    total_records = len(parsed_db.rows) + len(parsed_db.documents)
    total_structures = len(parsed_db.tables) + len(parsed_db.collections)

    broadcast_event(
        "status",
        {
            "text": f"Parsed {total_structures} tables/collections, {total_records} records. Scanning for vulnerabilities...",
            "progress": 0.20,
        },
    )
    await asyncio.sleep(0.05)

    scanner = VulnerabilityScanner()

    # Progress reporting with rate-limiting for large databases
    def progress_cb(msg: str, pct: float, finding: Optional[VulnerabilityFinding]):
        broadcast_event(
            "scan_step",
            {
                "message": msg,
                "progress": 0.20 + (pct * 0.75),
                "finding": finding.model_dump() if finding else None,
            },
        )

    summary = scanner.scan(parsed_db, progress_callback=progress_cb)

    # Register in active files list
    existing_file = next((f for f in APP_STATE["files"] if f["name"] == file_name), None)
    file_info = {
        "name": file_name,
        "type": summary.file_type,
        "size": f"{target_path.stat().st_size / 1024:.1f} KB",
        "scanned_at": summary.scan_timestamp,
        "findings_count": len(summary.findings),
    }
    if not existing_file:
        APP_STATE["files"].append(file_info)
    else:
        existing_file.update(file_info)

    # Cap findings list returned to web UI to first 250 for responsive rendering if huge
    capped_findings = [f.model_dump() for f in summary.findings[:250]]

    # Update app state
    APP_STATE["findings"] = capped_findings
    APP_STATE["total_findings_count"] = len(summary.findings)
    APP_STATE["total_records"] = summary.total_records
    APP_STATE["total_tables_collections"] = summary.total_tables_collections
    APP_STATE["risk_score"] = summary.risk_score
    APP_STATE["critical_count"] = summary.critical_count
    APP_STATE["high_count"] = summary.high_count
    APP_STATE["medium_count"] = summary.medium_count
    APP_STATE["low_count"] = summary.low_count
    APP_STATE["compliance_breakdown"] = summary.compliance_breakdown
    APP_STATE["last_scan_file"] = file_name
    APP_STATE["last_scan_type"] = summary.file_type
    APP_STATE["current_activity"] = (
        f"Audit complete for `{file_name}` ({summary.file_type}): Found {len(summary.findings)} vulnerabilities across {summary.total_records} records. Risk score: {summary.risk_score}/100."
    )

    summary_payload = summary.model_dump()
    summary_payload["findings"] = capped_findings  # Capped for SSE payload size
    summary_payload["total_findings_count"] = len(summary.findings)

    broadcast_event("scan_complete", {"summary": summary_payload, "state": APP_STATE})
    return summary_payload


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: Optional[UserProfile] = Depends(get_current_user),
):
    if user and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only users with Admin privileges can upload database files.")

    filename = file.filename or "uploaded.db"
    suffix = Path(filename).suffix.lower()
    allowed_suffixes = (".db", ".sqlite", ".sqlite3", ".sql", ".json", ".jsonl")
    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Allowed formats: {', '.join(allowed_suffixes)}",
        )

    save_path = UPLOAD_DIR / filename
    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    return {
        "status": "uploaded",
        "file_name": filename,
        "file_path": str(save_path),
        "size_bytes": len(content),
    }


@app.post("/api/reset")
async def reset_system(user: Optional[UserProfile] = Depends(get_current_user)):
    """Reset all scanned findings and uploads. Admin-only."""
    if user and user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Permission denied. Only Admin users can reset system data.")

    # Remove uploaded files
    for f in UPLOAD_DIR.glob("*"):
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass

    APP_STATE["files"] = []
    APP_STATE["findings"] = []
    APP_STATE["total_records"] = 0
    APP_STATE["total_tables_collections"] = 0
    APP_STATE["risk_score"] = 0
    APP_STATE["critical_count"] = 0
    APP_STATE["high_count"] = 0
    APP_STATE["medium_count"] = 0
    APP_STATE["low_count"] = 0
    APP_STATE["compliance_breakdown"] = {"PCI-DSS": 0, "GDPR": 0, "HIPAA": 0, "OWASP": 0}
    APP_STATE["last_scan_file"] = None
    APP_STATE["last_scan_type"] = None
    APP_STATE["current_activity"] = "System reset complete. All audited database records and findings have been purged."

    broadcast_event("system_reset", {"state": APP_STATE})
    return {"status": "success", "message": "All product data and findings have been successfully reset."}


@app.get("/api/report/markdown")
async def get_markdown_report():
    if not APP_STATE["last_scan_file"]:
        raise HTTPException(status_code=400, detail="No scan results available to report.")

    reporter = SecurityReporter()
    findings = [VulnerabilityFinding(**f) for f in APP_STATE["findings"]]
    summary = ScanSummary(
        file_name=APP_STATE["last_scan_file"],
        file_type=APP_STATE.get("last_scan_type") or "DATABASE",
        total_records=APP_STATE["total_records"],
        total_tables_collections=APP_STATE["total_tables_collections"],
        risk_score=APP_STATE["risk_score"],
        critical_count=APP_STATE["critical_count"],
        high_count=APP_STATE["high_count"],
        medium_count=APP_STATE["medium_count"],
        low_count=APP_STATE["low_count"],
        scan_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        findings=findings,
        compliance_breakdown=APP_STATE.get("compliance_breakdown") or {},
    )
    md_content = reporter.generate_markdown_report(summary)
    return {"markdown": md_content}


@app.get("/api/report/json")
async def get_json_report():
    if not APP_STATE["last_scan_file"]:
        raise HTTPException(status_code=400, detail="No scan results available.")
    return APP_STATE


# Serve Static UI
STATIC_DIR = Path("src/web/static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
