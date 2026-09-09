"""Comprehensive Vulnerability Scanner unit tests across SQLite .db, SQL dumps, and MongoDB."""
import pytest
from pathlib import Path

from src.dbsec.ingester_factory import ingest_database
from src.dbsec.scanner import VulnerabilityScanner
from src.dbsec.models import VulnerabilityCategory, VulnerabilitySeverity


def test_scanner_on_vulnerable_enterprise_db():
    parsed = ingest_database("samples/vulnerable_enterprise.db")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    # 10,500 records should produce high risk score and critical findings
    assert summary.risk_score == 100
    assert summary.critical_count > 1000
    assert summary.high_count > 100

    categories = {f.category for f in summary.findings}
    assert VulnerabilityCategory.PII_LEAK in categories
    assert VulnerabilityCategory.CREDENTIAL_LEAK in categories
    assert VulnerabilityCategory.WEAK_CRYPTOGRAPHY in categories
    assert VulnerabilityCategory.INSECURE_CONFIGURATION in categories
    assert VulnerabilityCategory.INSECURE_PRIVILEGE in categories
    assert VulnerabilityCategory.SCHEMA_RISK in categories

    # Compliance breakdown checks
    assert summary.compliance_breakdown["PCI-DSS"] > 1000
    assert summary.compliance_breakdown["GDPR"] > 1000
    assert summary.compliance_breakdown["OWASP"] > 100


def test_scanner_on_secure_store_db():
    parsed = ingest_database("samples/secure_store.db")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    # Hardened database should have 0 critical vulnerabilities and low risk score
    assert summary.critical_count == 0
    assert summary.high_count == 0
    assert summary.risk_score < 20


def test_scanner_on_vulnerable_sql():
    parsed = ingest_database("samples/vulnerable_store.sql")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    assert summary.risk_score > 50
    assert summary.critical_count >= 2
    categories = {f.category for f in summary.findings}
    assert VulnerabilityCategory.CREDENTIAL_LEAK in categories
    assert VulnerabilityCategory.PII_LEAK in categories
    assert VulnerabilityCategory.SQL_INJECTION in categories
    assert VulnerabilityCategory.INSECURE_PRIVILEGE in categories


def test_scanner_on_secure_sql():
    parsed = ingest_database("samples/secure_store.sql")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    assert summary.critical_count == 0
    assert summary.risk_score < 20


def test_scanner_on_mongo_users():
    parsed = ingest_database("samples/mongo_users.json")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    assert summary.critical_count >= 2
    categories = {f.category for f in summary.findings}
    assert VulnerabilityCategory.NOSQL_INJECTION in categories
    assert VulnerabilityCategory.PII_LEAK in categories
    assert VulnerabilityCategory.CREDENTIAL_LEAK in categories


def test_scanner_on_clean_mongo():
    parsed = ingest_database("samples/clean_mongo.json")
    scanner = VulnerabilityScanner()
    summary = scanner.scan(parsed)

    assert summary.critical_count == 0
    assert len(summary.findings) == 0
