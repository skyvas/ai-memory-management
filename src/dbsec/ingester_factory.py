"""Unified Ingester Factory for dbsec: routes file types to appropriate ingester."""
from pathlib import Path
from src.dbsec.models import ParsedDatabase
from src.dbsec.sqlite_ingester import SQLiteIngester
from src.dbsec.sql_ingester import SQLIngester
from src.dbsec.mongo_ingester import MongoIngester


def get_ingester_for_file(file_path: str):
    """Returns the appropriate ingester instance based on file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix in (".db", ".sqlite", ".sqlite3"):
        return SQLiteIngester()
    elif suffix == ".sql":
        return SQLIngester()
    elif suffix in (".json", ".jsonl"):
        return MongoIngester()
    else:
        raise ValueError(
            f"Unsupported file format '{suffix}'. Supported formats: .db, .sqlite, .sqlite3, .sql, .json, .jsonl"
        )


def ingest_database(file_path: str) -> ParsedDatabase:
    """Convenience function to ingest any supported database file."""
    ingester = get_ingester_for_file(file_path)
    return ingester.ingest_file(file_path)
