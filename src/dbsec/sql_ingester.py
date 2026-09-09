"""SQL Ingester for dbsec: parses schemas, INSERT data dumps, and queries."""
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlparse
from sqlparse.sql import Statement, IdentifierList, Identifier, Function

from src.dbsec.models import (
    ParsedDatabase,
    TableSchema,
    ColumnDef,
    DataRow,
    QueryStatement,
)


class SQLIngester:
    """Ingests and parses SQL files into structured schemas, row data, and queries."""

    def ingest_file(self, file_path: str) -> ParsedDatabase:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"SQL file not found: {file_path}")
        
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.ingest_content(content, source_file=path.name)

    def ingest_content(self, content: str, source_file: str = "input.sql") -> ParsedDatabase:
        lines = content.splitlines()
        parsed_db = ParsedDatabase(
            source_file=source_file,
            file_type="SQL",
            raw_lines=lines,
        )

        statements = sqlparse.split(content)
        current_offset = 0

        for stmt_str in statements:
            trimmed = stmt_str.strip()
            if not trimmed:
                continue

            # Locate line number in original content
            line_no = self._find_line_number(content, trimmed, current_offset)
            current_offset = content.find(trimmed, current_offset) + len(trimmed)

            # Strip leading comments to detect statement type accurately
            stmt_body = re.sub(r"^(?:--[^\n]*\n|\/\*.*?\*\/|\s+)+", "", trimmed, flags=re.DOTALL).strip()
            upper = stmt_body.upper()
            if upper.startswith("CREATE TABLE"):
                table = self._parse_create_table(stmt_body, line_no)
                if table:
                    parsed_db.tables.append(table)
            elif upper.startswith("INSERT INTO") or upper.startswith("INSERT"):
                rows = self._parse_insert(stmt_body, line_no)
                parsed_db.rows.extend(rows)
            else:
                # Queries or admin statements (SELECT, UPDATE, DELETE, GRANT, etc.)
                q_type = stmt_body.split()[0].upper() if stmt_body.split() else "SQL"
                parsed_db.queries.append(
                    QueryStatement(
                        query_text=trimmed,
                        line_number=line_no,
                        query_type=q_type,
                        dialect="SQL",
                    )
                )

        return parsed_db

    def _find_line_number(self, full_text: str, snippet: str, search_start: int) -> int:
        idx = full_text.find(snippet[:50], search_start)
        if idx == -1:
            idx = full_text.find(snippet[:50])
        if idx == -1:
            return 1
        return full_text[:idx].count("\n") + 1

    def _parse_create_table(self, stmt: str, line_no: int) -> Optional[TableSchema]:
        # Regex to capture table name and column definition block
        match = re.search(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([`\"\']?[\w\.]+[`\"\']?)\s*\((.*)\)",
            stmt,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return None

        raw_name = match.group(1).strip("`\"'")
        body = match.group(2)
        columns: List[ColumnDef] = []
        pk_name = None

        # Split column definitions safely (respecting commas inside types like NUMERIC(10,2))
        col_defs = self._split_column_defs(body)
        for col_def in col_defs:
            col_def_trimmed = col_def.strip()
            if not col_def_trimmed:
                continue
            
            upper_col = col_def_trimmed.upper()
            if upper_col.startswith("PRIMARY KEY"):
                pk_match = re.search(r"PRIMARY\s+KEY\s*\(([`\"\']?[\w]+[`\"\']?)\)", col_def_trimmed, re.I)
                if pk_match:
                    pk_name = pk_match.group(1).strip("`\"'")
                continue
            if upper_col.startswith("CONSTRAINT") or upper_col.startswith("FOREIGN KEY") or upper_col.startswith("KEY"):
                continue

            # Normal column definition: col_name data_type [constraints]
            parts = col_def_trimmed.split(None, 2)
            if len(parts) >= 2:
                c_name = parts[0].strip("`\"'")
                c_type = parts[1].upper()
                c_rest = parts[2].upper() if len(parts) > 2 else ""

                is_pk = "PRIMARY KEY" in c_rest
                if is_pk:
                    pk_name = c_name
                is_nullable = "NOT NULL" not in c_rest

                columns.append(
                    ColumnDef(
                        name=c_name,
                        data_type=c_type,
                        nullable=is_nullable,
                        is_primary_key=is_pk,
                    )
                )

        return TableSchema(
            name=raw_name,
            columns=columns,
            primary_key=pk_name,
            line_number=line_no,
        )

    def _split_column_defs(self, body: str) -> List[str]:
        items = []
        current = []
        depth = 0
        for char in body:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 0:
                items.append("".join(current))
                current = []
                continue
            current.append(char)
        if current:
            items.append("".join(current))
        return items

    def _parse_insert(self, stmt: str, line_no: int) -> List[DataRow]:
        # Matches: INSERT INTO table_name [(col1, col2)] VALUES (val1, val2), (val3, val4)
        match = re.search(
            r"INSERT\s+INTO\s+([`\"\']?[\w\.]+[`\"\']?)\s*(?:\((.*?)\))?\s*VALUES\s*(.*)",
            stmt,
            re.DOTALL | re.IGNORECASE,
        )
        if not match:
            return []

        table_name = match.group(1).strip("`\"'")
        raw_cols = match.group(2)
        raw_vals = match.group(3).rstrip(";")

        columns = []
        if raw_cols:
            columns = [c.strip().strip("`\"'") for c in raw_cols.split(",")]

        # Split multiple row value tuples: (val1, val2), (val3, val4)
        tuples = self._extract_value_tuples(raw_vals)
        rows: List[DataRow] = []

        for idx, t_str in enumerate(tuples):
            parsed_vals = self._parse_row_values(t_str)
            val_dict: Dict[str, Any] = {}

            if columns and len(columns) == len(parsed_vals):
                for col_name, val in zip(columns, parsed_vals):
                    val_dict[col_name] = val
            else:
                for v_idx, val in enumerate(parsed_vals):
                    col_key = columns[v_idx] if v_idx < len(columns) else f"col_{v_idx+1}"
                    val_dict[col_key] = val

            rows.append(
                DataRow(
                    table_name=table_name,
                    row_index=idx + 1,
                    values=val_dict,
                    line_number=line_no,
                    raw_statement=stmt[:200],
                )
            )

        return rows

    def _extract_value_tuples(self, raw_vals: str) -> List[str]:
        tuples = []
        in_string = False
        quote_char = None
        escape = False
        depth = 0
        current = []

        for char in raw_vals:
            if in_string:
                current.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote_char:
                    in_string = False
            else:
                if char in ("'", '"'):
                    in_string = True
                    quote_char = char
                    current.append(char)
                elif char == "(":
                    depth += 1
                    current = []
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        tuples.append("".join(current))
                        current = []
                elif depth > 0:
                    current.append(char)

        return tuples

    def _parse_row_values(self, tuple_content: str) -> List[Any]:
        # Split comma-separated values respecting quotes
        vals = []
        in_string = False
        quote_char = None
        escape = False
        current = []

        for char in tuple_content:
            if in_string:
                current.append(char)
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == quote_char:
                    in_string = False
            else:
                if char in ("'", '"'):
                    in_string = True
                    quote_char = char
                    current.append(char)
                elif char == ",":
                    vals.append(self._clean_scalar("".join(current).strip()))
                    current = []
                else:
                    current.append(char)

        if current:
            vals.append(self._clean_scalar("".join(current).strip()))
        return vals

    def _clean_scalar(self, val_str: str) -> Any:
        if not val_str:
            return None
        if val_str.upper() == "NULL":
            return None
        if (val_str.startswith("'") and val_str.endswith("'")) or (
            val_str.startswith('"') and val_str.endswith('"')
        ):
            return val_str[1:-1]
        try:
            if "." in val_str:
                return float(val_str)
            return int(val_str)
        except ValueError:
            return val_str
