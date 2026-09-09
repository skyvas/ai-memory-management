"""Data models for Database Security Tool (dbsec)."""
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid


class VulnerabilitySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class VulnerabilityCategory(str, Enum):
    PII_LEAK = "PII_LEAK"
    CREDENTIAL_LEAK = "CREDENTIAL_LEAK"
    WEAK_CRYPTOGRAPHY = "WEAK_CRYPTOGRAPHY"
    SQL_INJECTION = "SQL_INJECTION"
    NOSQL_INJECTION = "NOSQL_INJECTION"
    INSECURE_PRIVILEGE = "INSECURE_PRIVILEGE"
    SCHEMA_RISK = "SCHEMA_RISK"
    INSECURE_CONFIGURATION = "INSECURE_CONFIGURATION"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"


class UserProfile(BaseModel):
    username: str
    role: UserRole
    display_name: str


class VulnerabilityFinding(BaseModel):
    id: str = Field(default_factory=lambda: f"vuln_{uuid.uuid4().hex[:8]}")
    title: str
    category: VulnerabilityCategory
    severity: VulnerabilitySeverity
    file_name: str
    line_number: Optional[int] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    snippet: str
    remediation: str
    evidence: str
    cwe_id: Optional[str] = None
    compliance_tags: List[str] = Field(default_factory=list)
    confidence: float = 0.95


class ColumnDef(BaseModel):
    name: str
    data_type: str
    nullable: bool = True
    is_primary_key: bool = False
    default_value: Optional[str] = None


class TableSchema(BaseModel):
    name: str
    columns: List[ColumnDef] = Field(default_factory=list)
    primary_key: Optional[str] = None
    line_number: Optional[int] = None


class PragmaSetting(BaseModel):
    name: str
    value: Any
    is_secure: bool = True
    recommendation: Optional[str] = None


class DataRow(BaseModel):
    table_name: str
    row_index: int
    values: Dict[str, Any] = Field(default_factory=dict)
    line_number: Optional[int] = None
    raw_statement: str = ""


class MongoDocument(BaseModel):
    collection_name: str
    doc_index: int
    data: Dict[str, Any] = Field(default_factory=dict)
    line_number: Optional[int] = None
    raw_text: str = ""


class MongoCollection(BaseModel):
    name: str
    document_count: int = 0
    sample_fields: List[str] = Field(default_factory=list)


class QueryStatement(BaseModel):
    query_text: str
    line_number: Optional[int] = None
    query_type: str = "SELECT"
    dialect: str = "SQL"  # "SQL", "SQLITE", or "MONGO"


class ParsedDatabase(BaseModel):
    source_file: str
    file_type: str  # "SQL", "SQLITE", or "MONGO"
    tables: List[TableSchema] = Field(default_factory=list)
    rows: List[DataRow] = Field(default_factory=list)
    collections: List[MongoCollection] = Field(default_factory=list)
    documents: List[MongoDocument] = Field(default_factory=list)
    queries: List[QueryStatement] = Field(default_factory=list)
    pragmas: List[PragmaSetting] = Field(default_factory=list)
    raw_lines: List[str] = Field(default_factory=list)


class ScanSummary(BaseModel):
    file_name: str
    file_type: str
    total_records: int = 0
    total_tables_collections: int = 0
    risk_score: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    scan_timestamp: str
    findings: List[VulnerabilityFinding] = Field(default_factory=list)
    compliance_breakdown: Dict[str, int] = Field(default_factory=dict)
