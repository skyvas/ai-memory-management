"""SQLite binary database ingester for dbsec."""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.dbsec.models import (
    ParsedDatabase,
    TableSchema,
    ColumnDef,
    DataRow,
    QueryStatement,
    PragmaSetting,
)


class SQLiteIngester:
    """Ingests native SQLite binary databases (.db, .sqlite, .sqlite3).

    Extracts table schemas, column metadata, row contents, views, triggers,
    and security PRAGMA settings in read-only mode.
    """

    def __init__(self, max_rows_per_table: int = 50000):
        self.max_rows_per_table = max_rows_per_table

    def ingest_file(self, file_path: str) -> ParsedDatabase:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Database file not found: {file_path}")

        # Connect in URI read-only mode to guarantee zero modification
        try:
            conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
        except Exception:
            conn = sqlite3.connect(str(path))

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        parsed_db = ParsedDatabase(
            source_file=path.name,
            file_type="SQLITE",
            raw_lines=[],
        )

        try:
            # 1. Audit Security PRAGMAs
            self._audit_pragmas(cursor, parsed_db)

            # 2. Extract Schemas, Views, Triggers from sqlite_master
            self._extract_schema_and_queries(cursor, parsed_db)

            # 3. Ingest Data Rows across user tables
            self._extract_rows(cursor, parsed_db)

        finally:
            conn.close()

        return parsed_db

    def _audit_pragmas(self, cursor: sqlite3.Cursor, parsed_db: ParsedDatabase):
        """Audits database engine security parameters."""
        # Check secure_delete
        try:
            cursor.execute("PRAGMA secure_delete")
            row = cursor.fetchone()
            sec_del = row[0] if row else 0
            is_secure = sec_del in (1, 2)
            parsed_db.pragmas.append(
                PragmaSetting(
                    name="secure_delete",
                    value=sec_del,
                    is_secure=is_secure,
                    recommendation=(
                        "PRAGMA secure_delete is enabled."
                        if is_secure
                        else "Enable `PRAGMA secure_delete = ON` to overwrite deleted content with zeros and prevent forensic data recovery."
                    ),
                )
            )
        except Exception:
            pass

        # Check foreign_keys
        try:
            cursor.execute("PRAGMA foreign_keys")
            row = cursor.fetchone()
            fk_val = row[0] if row else 0
            is_fk_on = fk_val == 1
            parsed_db.pragmas.append(
                PragmaSetting(
                    name="foreign_keys",
                    value=fk_val,
                    is_secure=is_fk_on,
                    recommendation=(
                        "Foreign key constraints enforced."
                        if is_fk_on
                        else "Enable `PRAGMA foreign_keys = ON` to enforce referential integrity and prevent orphaned sensitive records."
                    ),
                )
            )
        except Exception:
            pass

        # Check auto_vacuum (persistent in DB header: 0=NONE, 1=FULL, 2=INCREMENTAL)
        try:
            cursor.execute("PRAGMA auto_vacuum")
            row = cursor.fetchone()
            av_val = int(row[0]) if row else 0
            is_av_secure = av_val in (1, 2)
            parsed_db.pragmas.append(
                PragmaSetting(
                    name="auto_vacuum",
                    value=av_val,
                    is_secure=is_av_secure,
                    recommendation=(
                        "Auto-vacuum is active, automatically reclaiming deleted page space."
                        if is_av_secure
                        else "Enable `PRAGMA auto_vacuum = FULL (1)` to reclaim deleted page space and prevent forensic recovery."
                    ),
                )
            )
        except Exception:
            pass

        # Check journal_mode (persistent in DB header: DELETE, WAL, MEMORY, OFF, etc.)
        try:
            cursor.execute("PRAGMA journal_mode")
            row = cursor.fetchone()
            j_mode = str(row[0]).upper() if row else "DELETE"
            is_j_secure = (j_mode == "WAL")
            parsed_db.pragmas.append(
                PragmaSetting(
                    name="journal_mode",
                    value=j_mode,
                    is_secure=is_j_secure,
                    recommendation=(
                        f"Journal mode `{j_mode}` (Write-Ahead Logging) provides optimal crash durability."
                        if is_j_secure
                        else f"Journal mode is `{j_mode}`. Upgrade to WAL (`PRAGMA journal_mode = WAL`) for concurrent read/write isolation."
                    ),
                )
            )
        except Exception:
            pass

    def _extract_schema_and_queries(self, cursor: sqlite3.Cursor, parsed_db: ParsedDatabase):
        """Extracts table DDL, columns, primary keys, views, and triggers."""
        cursor.execute(
            "SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
        items = cursor.fetchall()

        for item in items:
            item_type = item["type"]
            item_name = item["name"]
            item_sql = item["sql"] or ""

            if item_type == "table":
                # Extract columns via PRAGMA table_info
                cursor.execute(f'PRAGMA table_info("{item_name}")')
                col_rows = cursor.fetchall()
                cols: List[ColumnDef] = []
                pk_col = None

                for cr in col_rows:
                    col_name = cr[1]
                    col_type = cr[2] or "TEXT"
                    not_null = bool(cr[3])
                    dflt_val = str(cr[4]) if cr[4] is not None else None
                    is_pk = bool(cr[5])
                    if is_pk:
                        pk_col = col_name

                    cols.append(
                        ColumnDef(
                            name=col_name,
                            data_type=col_type,
                            nullable=not not_null,
                            is_primary_key=is_pk,
                            default_value=dflt_val,
                        )
                    )

                parsed_db.tables.append(
                    TableSchema(
                        name=item_name,
                        columns=cols,
                        primary_key=pk_col,
                        line_number=None,
                    )
                )

                if item_sql:
                    parsed_db.raw_lines.append(item_sql)

            elif item_type in ("view", "trigger"):
                parsed_db.queries.append(
                    QueryStatement(
                        query_text=item_sql,
                        line_number=None,
                        query_type=item_type.upper(),
                        dialect="SQLITE",
                    )
                )

    def _extract_rows(self, cursor: sqlite3.Cursor, parsed_db: ParsedDatabase):
        """Extracts data rows from all tables in chunked streams."""
        row_counter = 0
        for table in parsed_db.tables:
            table_name = table.name
            try:
                cursor.execute(f'SELECT * FROM "{table_name}" LIMIT ?', (self.max_rows_per_table,))
                col_names = [desc[0] for desc in cursor.description] if cursor.description else []

                while True:
                    batch = cursor.fetchmany(1000)
                    if not batch:
                        break
                    for r in batch:
                        row_counter += 1
                        row_dict = {col: r[col] for col in col_names}
                        parsed_db.rows.append(
                            DataRow(
                                table_name=table_name,
                                row_index=row_counter,
                                values=row_dict,
                                line_number=row_counter,
                                raw_statement=f"RECORD #{row_counter} FROM {table_name}",
                            )
                        )
            except Exception:
                continue
