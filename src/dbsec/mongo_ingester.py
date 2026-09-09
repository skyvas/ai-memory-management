"""MongoDB Ingester for dbsec: parses JSON / JSONL documents, collections, and queries."""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.dbsec.models import (
    ParsedDatabase,
    MongoCollection,
    MongoDocument,
    QueryStatement,
)


class MongoIngester:
    """Ingests and parses MongoDB exports, JSON/JSONL document collections, and query objects."""

    def ingest_file(self, file_path: str) -> ParsedDatabase:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"MongoDB file not found: {file_path}")

        content = path.read_text(encoding="utf-8", errors="replace")
        return self.ingest_content(content, source_file=path.name)

    def ingest_content(self, content: str, source_file: str = "mongo_dump.json") -> ParsedDatabase:
        lines = content.splitlines()
        parsed_db = ParsedDatabase(
            source_file=source_file,
            file_type="MONGO",
            raw_lines=lines,
        )

        trimmed = content.strip()
        inferred_col_name = Path(source_file).stem.replace("_dump", "").replace(".json", "")

        # Try parsing as whole JSON first
        try:
            data = json.loads(trimmed)
            if isinstance(data, list):
                # Array of documents
                self._process_doc_list(data, inferred_col_name, parsed_db)
            elif isinstance(data, dict):
                # Could be a single document, a collection wrapper, or a query
                if "docs" in data and isinstance(data["docs"], list):
                    col = data.get("collection", inferred_col_name)
                    self._process_doc_list(data["docs"], col, parsed_db)
                elif "collections" in data and isinstance(data["collections"], dict):
                    for c_name, doc_list in data["collections"].items():
                        if isinstance(doc_list, list):
                            self._process_doc_list(doc_list, c_name, parsed_db)
                elif "query" in data or "$where" in str(data):
                    # Query object
                    parsed_db.queries.append(
                        QueryStatement(
                            query_text=json.dumps(data, indent=2),
                            line_number=1,
                            query_type="FIND",
                            dialect="MONGO",
                        )
                    )
                else:
                    # Single document
                    self._process_doc_list([data], inferred_col_name, parsed_db)
            return parsed_db
        except json.JSONDecodeError:
            pass

        # If not single JSON, parse line by line (JSONL format or MongoDB shell queries)
        doc_list = []
        for line_idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            if not line_str or line_str.startswith("//") or line_str.startswith("#"):
                continue

            # Check if line is a MongoDB query statement e.g. db.users.find({$where: ...})
            if line_str.startswith("db.") or "find(" in line_str or "aggregate(" in line_str:
                parsed_db.queries.append(
                    QueryStatement(
                        query_text=line_str,
                        line_number=line_idx,
                        query_type="MONGO_QUERY",
                        dialect="MONGO",
                    )
                )
                continue

            try:
                line_data = json.loads(line_str)
                if isinstance(line_data, dict):
                    doc_list.append((line_data, line_idx))
            except json.JSONDecodeError:
                continue

        if doc_list:
            collection = MongoCollection(name=inferred_col_name, document_count=len(doc_list))
            fields_set = set()
            for idx, (doc, line_no) in enumerate(doc_list, start=1):
                fields_set.update(doc.keys())
                parsed_db.documents.append(
                    MongoDocument(
                        collection_name=inferred_col_name,
                        doc_index=idx,
                        data=doc,
                        line_number=line_no,
                        raw_text=json.dumps(doc),
                    )
                )
            collection.sample_fields = list(fields_set)[:10]
            parsed_db.collections.append(collection)

        return parsed_db

    def _process_doc_list(
        self, docs: List[Dict[str, Any]], collection_name: str, parsed_db: ParsedDatabase
    ) -> None:
        collection = MongoCollection(name=collection_name, document_count=len(docs))
        fields_set = set()
        for idx, doc in enumerate(docs, start=1):
            if isinstance(doc, dict):
                fields_set.update(doc.keys())
                # If document contains query operators like $where, also register as a query
                if any(k.startswith("$") for k in doc.keys()) or any(
                    isinstance(v, dict) and any(subk.startswith("$") for subk in v.keys())
                    for v in doc.values()
                ):
                    parsed_db.queries.append(
                        QueryStatement(
                            query_text=json.dumps(doc),
                            line_number=idx,
                            query_type="MONGO_QUERY",
                            dialect="MONGO",
                        )
                    )

                parsed_db.documents.append(
                    MongoDocument(
                        collection_name=collection_name,
                        doc_index=idx,
                        data=doc,
                        line_number=idx,
                        raw_text=json.dumps(doc),
                    )
                )
        collection.sample_fields = list(fields_set)[:10]
        parsed_db.collections.append(collection)
