"""Unit tests for SQLiteIngester."""
import pytest
from pathlib import Path
from src.dbsec.sqlite_ingester import SQLiteIngester
from src.dbsec.models import ParsedDatabase


def test_sqlite_ingester_vulnerable_enterprise():
    db_path = Path("samples/vulnerable_enterprise.db")
    assert db_path.exists(), "samples/vulnerable_enterprise.db should exist"

    ingester = SQLiteIngester()
    parsed: ParsedDatabase = ingester.ingest_file(str(db_path))

    assert parsed.file_type == "SQLITE"
    assert parsed.source_file == "vulnerable_enterprise.db"

    # Verify tables
    table_names = {t.name for t in parsed.tables}
    assert "customers" in table_names
    assert "user_credentials" in table_names
    assert "payment_cards" in table_names
    assert "api_keys_and_tokens" in table_names
    assert "audit_logs" in table_names
    assert "unconstrained_profiles" in table_names

    # Verify total record count (10,500 entries)
    assert len(parsed.rows) >= 10500

    # Verify security PRAGMAs in vulnerable store
    pragma_map = {p.name: p for p in parsed.pragmas}
    assert "auto_vacuum" in pragma_map
    assert pragma_map["auto_vacuum"].is_secure is False  # 0 = NONE

    assert "journal_mode" in pragma_map
    assert pragma_map["journal_mode"].is_secure is False  # DELETE mode instead of WAL

    assert "foreign_keys" in pragma_map
    assert pragma_map["foreign_keys"].is_secure is False  # 0 = OFF by default

    # Verify triggers / views recorded
    assert len(parsed.queries) >= 1


def test_sqlite_ingester_secure_store():
    db_path = Path("samples/secure_store.db")
    assert db_path.exists(), "samples/secure_store.db should exist"

    ingester = SQLiteIngester()
    parsed: ParsedDatabase = ingester.ingest_file(str(db_path))

    assert parsed.file_type == "SQLITE"
    assert len(parsed.rows) == 1000

    # Verify PRAGMAs in hardened store
    pragma_map = {p.name: p for p in parsed.pragmas}
    assert "auto_vacuum" in pragma_map
    assert pragma_map["auto_vacuum"].is_secure is True  # 1 = FULL

    assert "journal_mode" in pragma_map
    assert pragma_map["journal_mode"].is_secure is True  # WAL mode
