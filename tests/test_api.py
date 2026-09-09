"""Integration tests for DataSec DB web API endpoints."""
import pytest
from fastapi.testclient import TestClient
from src.web.server import app

client = TestClient(app)


def test_api_samples_includes_sqlite_db():
    res = client.get("/api/samples")
    assert res.status_code == 200
    samples = res.json()
    sample_ids = {s["id"] for s in samples}

    assert "vulnerable_enterprise.db" in sample_ids
    assert "secure_store.db" in sample_ids
    assert "vulnerable_store.sql" in sample_ids
    assert "mongo_users.json" in sample_ids


def test_api_auth_login():
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin"})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["role"] == "ADMIN"

    # Test /api/auth/me with token
    token = data["token"]
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["authenticated"] is True


def test_api_scan_vulnerable_enterprise_db():
    res = client.post("/api/scan", json={"sample_id": "vulnerable_enterprise.db"})
    assert res.status_code == 200
    summary = res.json()

    assert summary["file_name"] == "vulnerable_enterprise.db"
    assert summary["file_type"] == "SQLITE"
    assert summary["total_records"] >= 10500
    assert summary["risk_score"] == 100
    assert summary["critical_count"] > 1000

    # Verify report endpoint
    rpt_res = client.get("/api/report/markdown")
    assert rpt_res.status_code == 200
    md = rpt_res.json()["markdown"]
    assert "Database Security Audit Report: vulnerable_enterprise.db" in md
    assert "Compliance Violations" in md


def test_api_scan_secure_store_db():
    res = client.post("/api/scan", json={"sample_id": "secure_store.db"})
    assert res.status_code == 200
    summary = res.json()

    assert summary["file_name"] == "secure_store.db"
    assert summary["critical_count"] == 0
    assert summary["risk_score"] < 20


def test_api_upload_invalid_extension():
    # Attempting to upload unsupported file format (.exe)
    res = client.post(
        "/api/upload",
        files={"file": ("malware.exe", b"binarycontent", "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported format" in res.json()["detail"]
