"""Comprehensive Vulnerability Scanner Engine for dbsec.

Audits binary SQLite databases (.db), SQL dumps (.sql), and MongoDB document stores (.json/.jsonl)
for cryptographic flaws, PII exposures, injection vectors, schema risks, and insecure engine PRAGMAs.
"""
import re
import datetime
from typing import List, Dict, Any, Optional, Callable

from src.dbsec.models import (
    ParsedDatabase,
    VulnerabilityFinding,
    VulnerabilityCategory,
    VulnerabilitySeverity,
    ScanSummary,
    DataRow,
    MongoDocument,
    QueryStatement,
    TableSchema,
    PragmaSetting,
)


class VulnerabilityScanner:
    """High-performance multi-vector database vulnerability scanner."""

    # Sensitive field regex patterns
    PASSWORD_FIELD_REGEX = re.compile(
        r"(password|passwd|pwd|pass_hash|secret_key|user_pass|user_password|auth_pass)", re.I
    )
    TOKEN_FIELD_REGEX = re.compile(
        r"(api_key|auth_token|secret_token|access_token|bearer_token|private_key|api_secret)", re.I
    )
    SSN_FIELD_REGEX = re.compile(r"(ssn|social_security|national_id|tax_id|sin_num)", re.I)
    CREDIT_CARD_FIELD_REGEX = re.compile(r"(credit_card|card_num|card_number|cc_num|pan|card_pan)", re.I)
    EMAIL_FIELD_REGEX = re.compile(r"(email|e_mail|user_email|contact_email)", re.I)
    PHONE_FIELD_REGEX = re.compile(r"(phone|mobile|telephone|cell_phone|contact_phone)", re.I)
    HEALTH_FIELD_REGEX = re.compile(r"(mrn|medical_record|patient_id|health_id|diagnosis)", re.I)

    # Cryptographic Hash Recognition
    BCRYPT_REGEX = re.compile(r"^\$2[aby]\$[0-9]{2}\$[A-Za-z0-9\.\/]{53}$")
    ARGON2_REGEX = re.compile(r"^\$argon2[id]?\$")
    PBKDF2_REGEX = re.compile(r"^(?:pbkdf2:|\$pbkdf2-)")
    MD5_REGEX = re.compile(r"^[a-fA-F0-9]{32}$")
    SHA1_REGEX = re.compile(r"^[a-fA-F0-9]{40}$")
    SHA256_RAW_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")

    # High-Entropy Secrets & Key Signatures
    PRIVATE_KEY_REGEX = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")
    AWS_KEY_REGEX = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
    GITHUB_TOKEN_REGEX = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,}\b")
    STRIPE_KEY_REGEX = re.compile(r"\bsk_(?:live|test)_[0-9a-zA-Z]{24,}\b")
    JWT_REGEX = re.compile(r"\beyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]+\b")

    # Credit Card Patterns (Visa, MC, Amex, Discover)
    CC_REGEX = re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
    )
    CC_DELIM_REGEX = re.compile(
        r"\b(?:\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4}|\d{4}[-\s]\d{6}[-\s]\d{5})\b"
    )

    # Identifiers
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_REGEX = re.compile(r"\b(?:\+?1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

    # Trivial / Default Passwords
    DEFAULT_PASSWORDS = {
        "admin", "password", "123456", "root", "toor", "qwerty", "12345678", "pass123", "guest"
    }

    def scan(
        self,
        parsed_db: ParsedDatabase,
        progress_callback: Optional[Callable[[str, float, Optional[VulnerabilityFinding]], None]] = None,
    ) -> ScanSummary:
        findings: List[VulnerabilityFinding] = []
        total_items = (
            len(parsed_db.pragmas)
            + len(parsed_db.tables)
            + len(parsed_db.rows)
            + len(parsed_db.collections)
            + len(parsed_db.documents)
            + len(parsed_db.queries)
        )
        processed = 0

        def update_progress(msg: str, finding: Optional[VulnerabilityFinding] = None, force: bool = False):
            nonlocal processed
            processed += 1
            if progress_callback:
                # Update every 500 items or whenever a vulnerability finding occurs
                if force or finding is not None or processed % 500 == 0 or processed >= total_items:
                    pct = min(1.0, processed / max(1, total_items))
                    progress_callback(msg, pct, finding)

        # 1. Audit SQLite PRAGMA Configurations
        for pragma in parsed_db.pragmas:
            p_finding = self._scan_pragma(pragma, parsed_db.source_file)
            if p_finding:
                findings.append(p_finding)
                update_progress(f"Found PRAGMA security risk: `{pragma.name}`", p_finding, force=True)
            else:
                update_progress(f"PRAGMA `{pragma.name}` verified secure.")

        # 2. Audit Table Schemas (DDL / SQLite table_info)
        for table in parsed_db.tables:
            t_findings = self._scan_table_schema(table, parsed_db.source_file)
            for f in t_findings:
                findings.append(f)
                update_progress(f"Found schema risk in `{table.name}`", f, force=True)
            if not t_findings:
                update_progress(f"Verified schema for table `{table.name}`")

        # 3. Audit Data Rows (SQLite & SQL Dumps)
        for row in parsed_db.rows:
            r_findings = self._scan_data_row(row, parsed_db.source_file)
            for f in r_findings:
                findings.append(f)
                update_progress(f"Found risk in `{row.table_name}` row #{row.row_index}", f, force=True)
            if not r_findings:
                update_progress(f"Audited row #{row.row_index} in `{row.table_name}`")

        # 4. Audit Mongo Documents
        for doc in parsed_db.documents:
            d_findings = self._scan_mongo_document(doc, parsed_db.source_file)
            for f in d_findings:
                findings.append(f)
                update_progress(f"Found risk in collection `{doc.collection_name}` doc #{doc.doc_index}", f, force=True)
            if not d_findings:
                update_progress(f"Audited doc #{doc.doc_index} in `{doc.collection_name}`")

        # 5. Audit Queries, Triggers, and Views
        for q in parsed_db.queries:
            q_findings = self._scan_query(q, parsed_db.source_file)
            for f in q_findings:
                findings.append(f)
                update_progress(f"Found query injection risk at line {q.line_number or 'schema'}", f, force=True)
            if not q_findings:
                update_progress(f"Audited query {q.query_type}")

        # Compute summary metrics and compliance breakdown
        summary = self._build_summary(parsed_db, findings)
        return summary

    def _scan_pragma(self, pragma: PragmaSetting, file_name: str) -> Optional[VulnerabilityFinding]:
        if pragma.name == "secure_delete" and not pragma.is_secure:
            return VulnerabilityFinding(
                title="Insecure SQLite Configuration: `secure_delete` Disabled",
                category=VulnerabilityCategory.INSECURE_CONFIGURATION,
                severity=VulnerabilitySeverity.HIGH,
                file_name=file_name,
                snippet="PRAGMA secure_delete = 0;",
                remediation="Execute `PRAGMA secure_delete = ON;` during connection initialization to overwrite deleted rows with zeros and prevent forensic data reconstruction.",
                evidence="PRAGMA secure_delete is OFF (0). Deleted records and PII remain recoverable from unallocated database pages.",
                cwe_id="CWE-312",
                compliance_tags=["GDPR-Art-17", "PCI-DSS-Req-3.4", "CIS-SQLite-1.1"],
                confidence=0.99,
            )
        elif pragma.name == "foreign_keys" and not pragma.is_secure:
            return VulnerabilityFinding(
                title="Insecure SQLite Configuration: Foreign Key Enforcement Disabled",
                category=VulnerabilityCategory.INSECURE_CONFIGURATION,
                severity=VulnerabilitySeverity.MEDIUM,
                file_name=file_name,
                snippet="PRAGMA foreign_keys = 0;",
                remediation="Execute `PRAGMA foreign_keys = ON;` to enforce relational integrity constraints and prevent orphaned data records.",
                evidence="PRAGMA foreign_keys is OFF (0). Relational constraints and cascading deletes are bypassed.",
                cwe_id="CWE-1025",
                compliance_tags=["OWASP-A01:2021", "CIS-SQLite-1.2"],
                confidence=0.98,
            )
        elif pragma.name == "journal_mode" and not pragma.is_secure:
            return VulnerabilityFinding(
                title=f"Insecure SQLite Transaction Journaling: `{pragma.value}`",
                category=VulnerabilityCategory.INSECURE_CONFIGURATION,
                severity=VulnerabilitySeverity.HIGH,
                file_name=file_name,
                snippet=f"PRAGMA journal_mode = {pragma.value};",
                remediation="Use WAL (Write-Ahead Logging) or DELETE journal mode to ensure atomic write guarantees and transaction durability.",
                evidence=f"Journal mode is set to '{pragma.value}', bypassing crash recovery safeguards.",
                cwe_id="CWE-754",
                compliance_tags=["CIS-SQLite-1.3"],
                confidence=0.95,
            )
        return None

    def _scan_table_schema(self, table: TableSchema, file_name: str) -> List[VulnerabilityFinding]:
        findings = []
        lower_name = table.name.lower()

        # Check 1: Missing primary key on sensitive tables
        if not table.primary_key:
            if any(k in lower_name for k in ("user", "account", "customer", "member", "auth", "profile", "cred")):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Missing Primary Key on Sensitive Entity `{table.name}`",
                        category=VulnerabilityCategory.SCHEMA_RISK,
                        severity=VulnerabilitySeverity.MEDIUM,
                        file_name=file_name,
                        table_name=table.name,
                        line_number=table.line_number,
                        snippet=f"CREATE TABLE {table.name} ( ... ) -- No PRIMARY KEY",
                        remediation="Define a strong immutable PRIMARY KEY (e.g. UUIDv4 or BIGSERIAL) to guarantee entity uniqueness and prevent collision vulnerabilities.",
                        evidence=f"Table `{table.name}` stores sensitive user records without a PRIMARY KEY constraint.",
                        cwe_id="CWE-1025",
                        compliance_tags=["OWASP-A01:2021", "PCI-DSS-Req-6.5"],
                    )
                )

        # Check 2: Insecure default privileges in column definitions
        for col in table.columns:
            if col.default_value is not None:
                dflt = col.default_value.strip("'\" ").lower()
                if col.name.lower() in ("is_admin", "is_superuser", "role", "privilege"):
                    if dflt in ("1", "true", "admin", "superuser", "root"):
                        findings.append(
                            VulnerabilityFinding(
                                title=f"Insecure Privilege Escalation Default on `{table.name}.{col.name}`",
                                category=VulnerabilityCategory.INSECURE_PRIVILEGE,
                                severity=VulnerabilitySeverity.HIGH,
                                file_name=file_name,
                                table_name=table.name,
                                column_name=col.name,
                                line_number=table.line_number,
                                snippet=f"{col.name} {col.data_type} DEFAULT {col.default_value}",
                                remediation="Default all new accounts to least privilege (`is_admin DEFAULT 0` or `role DEFAULT 'user'`). Explicitly grant administrative privileges via controlled provisioning workflows.",
                                evidence=f"New user records automatically receive elevated permissions via DEFAULT `{col.default_value}`.",
                                cwe_id="CWE-276",
                                compliance_tags=["OWASP-A01:2021", "PCI-DSS-Req-7.2"],
                            )
                        )

        return findings

    def _scan_data_row(self, row: DataRow, file_name: str) -> List[VulnerabilityFinding]:
        findings = []

        for col_name, val in row.values.items():
            if val is None:
                continue
            str_val = str(val).strip()
            if not str_val:
                continue

            col_lower = col_name.lower()

            # 1. Check Passwords & Cryptographic Hashes
            if self.PASSWORD_FIELD_REGEX.search(col_lower):
                # Check for Trivial / Default Passwords
                if str_val.lower() in self.DEFAULT_PASSWORDS:
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Default / Trivial Password Detected in `{row.table_name}.{col_name}`",
                            category=VulnerabilityCategory.CREDENTIAL_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            table_name=row.table_name,
                            column_name=col_name,
                            line_number=row.line_number,
                            snippet=f"{col_name} = '{str_val}'",
                            remediation="Enforce strict password complexity and reject default passwords (e.g. 'admin', 'password'). Use Argon2id salted hashing.",
                            evidence=f"Common trivial password '{str_val}' found in record #{row.row_index}.",
                            cwe_id="CWE-521",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A07:2021", "NIST-800-63B"],
                            confidence=0.99,
                        )
                    )
                # Check for Weak / Obsolete Hashing
                elif self.MD5_REGEX.match(str_val):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Cryptographically Broken Hash (MD5) in `{row.table_name}.{col_name}`",
                            category=VulnerabilityCategory.WEAK_CRYPTOGRAPHY,
                            severity=VulnerabilitySeverity.HIGH,
                            file_name=file_name,
                            table_name=row.table_name,
                            column_name=col_name,
                            line_number=row.line_number,
                            snippet=f"{col_name} = '{str_val}'",
                            remediation="MD5 is vulnerable to collision attacks and rainbow table inversion. Upgrade to memory-hard Argon2id or bcrypt ($2b$12$) with cryptographically secure random salts.",
                            evidence=f"32-character hexadecimal MD5 hash detected in password field (Record #{row.row_index}).",
                            cwe_id="CWE-328",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A02:2021", "NIST-SP-800-131A"],
                            confidence=0.96,
                        )
                    )
                elif self.SHA1_REGEX.match(str_val):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Deprecated Cryptographic Hash (SHA-1) in `{row.table_name}.{col_name}`",
                            category=VulnerabilityCategory.WEAK_CRYPTOGRAPHY,
                            severity=VulnerabilitySeverity.HIGH,
                            file_name=file_name,
                            table_name=row.table_name,
                            column_name=col_name,
                            line_number=row.line_number,
                            snippet=f"{col_name} = '{str_val}'",
                            remediation="SHA-1 has been formally deprecated by NIST due to collision vulnerabilities. Migrate to Argon2id or PBKDF2 with SHA-256/SHA-512.",
                            evidence=f"40-character hexadecimal SHA-1 hash detected in credential field (Record #{row.row_index}).",
                            cwe_id="CWE-328",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A02:2021"],
                            confidence=0.95,
                        )
                    )
                # Check for Plaintext Password
                elif not self._is_modern_hash(str_val):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Plaintext Password Detected in `{row.table_name}.{col_name}`",
                            category=VulnerabilityCategory.CREDENTIAL_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            table_name=row.table_name,
                            column_name=col_name,
                            line_number=row.line_number,
                            snippet=f"{col_name} = '{self._mask(str_val)}'",
                            remediation="Never persist unhashed passwords. Use salted Argon2id ($argon2id$) or bcrypt ($2b$) before saving credentials.",
                            evidence=f"Unhashed plaintext credential stored in column `{col_name}` (Record #{row.row_index}).",
                            cwe_id="CWE-256",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A07:2021", "GDPR-Art-32"],
                            confidence=0.99,
                        )
                    )

            # 2. Check for Exposed Private Keys
            if self.PRIVATE_KEY_REGEX.search(str_val):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Hardcoded Private Cryptographic Key in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '-----BEGIN PRIVATE KEY...'",
                        remediation="Revoke and rotate the exposed private key immediately. Store private keys in an encrypted Hardware Security Module (HSM) or cloud Secret Manager.",
                        evidence=f"PEM-encoded private key header detected in record #{row.row_index}.",
                        cwe_id="CWE-798",
                        compliance_tags=["PCI-DSS-Req-3.5", "OWASP-A07:2021"],
                        confidence=0.99,
                    )
                )

            # 3. Check for Cloud Secrets / API Keys
            if self.AWS_KEY_REGEX.search(str_val):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Exposed AWS Access Key in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{str_val[:8]}...'",
                        remediation="Immediately revoke the exposed AWS key in IAM. Utilize IAM Roles / Instance Profiles instead of storing static cloud credentials.",
                        evidence=f"Active AWS Access Key ID pattern (AKIA...) found in record #{row.row_index}.",
                        cwe_id="CWE-798",
                        compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A07:2021"],
                        confidence=0.98,
                    )
                )
            elif self.GITHUB_TOKEN_REGEX.search(str_val):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Exposed GitHub Personal Access Token in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{str_val[:8]}...'",
                        remediation="Revoke token on GitHub and migrate to short-lived GitHub App tokens or Secret Managers.",
                        evidence=f"GitHub token prefix detected in record #{row.row_index}.",
                        cwe_id="CWE-798",
                        compliance_tags=["OWASP-A07:2021"],
                        confidence=0.99,
                    )
                )
            elif self.STRIPE_KEY_REGEX.search(str_val):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Exposed Stripe Secret Key in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{str_val[:10]}...'",
                        remediation="Roll the compromised Stripe secret key in the Stripe Dashboard immediately.",
                        evidence=f"Stripe secret key pattern detected in record #{row.row_index}.",
                        cwe_id="CWE-798",
                        compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A07:2021"],
                        confidence=0.99,
                    )
                )
            elif self.JWT_REGEX.search(str_val) or (self.TOKEN_FIELD_REGEX.search(col_lower) and len(str_val) > 24):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Plaintext Auth Token / Secret in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{str_val[:8]}...{str_val[-4:]}'",
                        remediation="Store session and bearer tokens in ephemeral cache stores (e.g. Redis) with short TTLs rather than database tables.",
                        evidence=f"High-entropy auth secret detected in column `{col_name}` (Record #{row.row_index}).",
                        cwe_id="CWE-798",
                        compliance_tags=["OWASP-A07:2021"],
                        confidence=0.92,
                    )
                )

            # 4. Check for Credit Cards (PAN)
            cc_candidate = self._find_credit_card(str_val)
            if cc_candidate or self.CREDIT_CARD_FIELD_REGEX.search(col_lower):
                card_num = cc_candidate or str_val
                clean_num = re.sub(r"[-\s]", "", card_num)
                if self._validate_luhn(clean_num):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Plaintext Payment Card (PAN) Exposed in `{row.table_name}.{col_name}`",
                            category=VulnerabilityCategory.PII_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            table_name=row.table_name,
                            column_name=col_name,
                            line_number=row.line_number,
                            snippet=f"{col_name} = '{self._mask_card(card_num)}'",
                            remediation="Violates PCI-DSS Requirement 3.4. Tokenize cardholder data or encrypt primary account numbers (PAN) using authenticated AES-256-GCM encryption at rest.",
                            evidence=f"Valid payment card verified via Luhn check in record #{row.row_index}.",
                            cwe_id="CWE-311",
                            compliance_tags=["PCI-DSS-Req-3.4", "GDPR-Art-32"],
                            confidence=0.99,
                        )
                    )

            # 5. Check for SSNs
            if self.SSN_REGEX.search(str_val) or (self.SSN_FIELD_REGEX.search(col_lower) and len(re.sub(r"\D", "", str_val)) == 9):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Plaintext Social Security Number (SSN) in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.PII_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{self._mask(str_val, keep=4)}'",
                        remediation="Mask or pseudonymize government-issued national identifiers at rest using column-level envelope encryption under GDPR and CCPA standards.",
                        evidence=f"SSN pattern detected in record #{row.row_index}.",
                        cwe_id="CWE-359",
                        compliance_tags=["GDPR-Art-32", "CCPA-1798.100"],
                        confidence=0.98,
                    )
                )

            # 6. Check for Healthcare Identifiers
            if self.HEALTH_FIELD_REGEX.search(col_lower) and len(str_val) > 4:
                findings.append(
                    VulnerabilityFinding(
                        title=f"Exposed Medical / Patient Identifier in `{row.table_name}.{col_name}`",
                        category=VulnerabilityCategory.PII_LEAK,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        table_name=row.table_name,
                        column_name=col_name,
                        line_number=row.line_number,
                        snippet=f"{col_name} = '{self._mask(str_val, keep=3)}'",
                        remediation="Apply HIPAA Security Rule §164.312 encryption to Protected Health Information (PHI) at rest.",
                        evidence=f"Medical / health record field `{col_name}` stored in plaintext (Record #{row.row_index}).",
                        cwe_id="CWE-359",
                        compliance_tags=["HIPAA-164.312"],
                        confidence=0.90,
                    )
                )

        return findings

    def _scan_mongo_document(self, doc: MongoDocument, file_name: str) -> List[VulnerabilityFinding]:
        findings = []

        def check_field(key: str, val: Any):
            if val is None:
                return
            str_val = str(val).strip()
            if not str_val:
                return

            key_lower = key.lower()

            # Password
            if self.PASSWORD_FIELD_REGEX.search(key_lower):
                if str_val.lower() in self.DEFAULT_PASSWORDS:
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Default / Trivial Password in MongoDB `{doc.collection_name}.{key}`",
                            category=VulnerabilityCategory.CREDENTIAL_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            line_number=doc.line_number,
                            snippet=f'"{key}": "{str_val}"',
                            remediation="Reject common default passwords and hash credentials with Argon2id.",
                            evidence=f"Default password '{str_val}' in document #{doc.doc_index}.",
                            cwe_id="CWE-521",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A07:2021"],
                        )
                    )
                elif self.MD5_REGEX.match(str_val):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Cryptographically Broken Hash (MD5) in MongoDB `{doc.collection_name}.{key}`",
                            category=VulnerabilityCategory.WEAK_CRYPTOGRAPHY,
                            severity=VulnerabilitySeverity.HIGH,
                            file_name=file_name,
                            line_number=doc.line_number,
                            snippet=f'"{key}": "{str_val}"',
                            remediation="Upgrade MD5 hashes to salted Argon2id or bcrypt.",
                            evidence=f"MD5 hash detected in MongoDB document #{doc.doc_index}.",
                            cwe_id="CWE-328",
                            compliance_tags=["PCI-DSS-Req-8.3", "OWASP-A02:2021"],
                        )
                    )
                elif not self._is_modern_hash(str_val):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Plaintext Password in MongoDB Collection `{doc.collection_name}.{key}`",
                            category=VulnerabilityCategory.CREDENTIAL_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            line_number=doc.line_number,
                            snippet=f'"{key}": "{self._mask(str_val)}"',
                            remediation="Hash passwords using Argon2id or bcrypt before persisting documents into MongoDB.",
                            evidence=f"Unhashed password in collection `{doc.collection_name}`, document #{doc.doc_index}.",
                            cwe_id="CWE-256",
                            compliance_tags=["PCI-DSS-Req-8.3", "GDPR-Art-32"],
                        )
                    )

            # Credit Card
            cc_candidate = self._find_credit_card(str_val)
            if cc_candidate or self.CREDIT_CARD_FIELD_REGEX.search(key_lower):
                card_num = cc_candidate or str_val
                clean_num = re.sub(r"[-\s]", "", card_num)
                if self._validate_luhn(clean_num):
                    findings.append(
                        VulnerabilityFinding(
                            title=f"Payment Card Data in MongoDB `{doc.collection_name}.{key}`",
                            category=VulnerabilityCategory.PII_LEAK,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            line_number=doc.line_number,
                            snippet=f'"{key}": "{self._mask_card(card_num)}"',
                            remediation="Tokenize card numbers per PCI-DSS standards; do not store full PANs in MongoDB document stores.",
                            evidence=f"Luhn-verified payment card number in document #{doc.doc_index}.",
                            cwe_id="CWE-311",
                            compliance_tags=["PCI-DSS-Req-3.4", "GDPR-Art-32"],
                        )
                    )

            # SSN
            if self.SSN_REGEX.search(str_val) or (self.SSN_FIELD_REGEX.search(key_lower) and len(re.sub(r"\D", "", str_val)) == 9):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Plaintext SSN in MongoDB `{doc.collection_name}.{key}`",
                        category=VulnerabilityCategory.PII_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        line_number=doc.line_number,
                        snippet=f'"{key}": "{self._mask(str_val, keep=4)}"',
                        remediation="Encrypt PII fields with client-side field-level encryption (CSFLE) in MongoDB.",
                        evidence=f"National ID / SSN pattern found in document #{doc.doc_index}.",
                        cwe_id="CWE-359",
                        compliance_tags=["GDPR-Art-32"],
                    )
                )

            # Secrets
            if self.PRIVATE_KEY_REGEX.search(str_val):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Private Key Exposed in MongoDB `{doc.collection_name}.{key}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        line_number=doc.line_number,
                        snippet=f'"{key}": "-----BEGIN PRIVATE KEY..."',
                        remediation="Store private keys in a secure key management service (KMS).",
                        evidence=f"Private key in document #{doc.doc_index}.",
                        cwe_id="CWE-798",
                        compliance_tags=["PCI-DSS-Req-3.5"],
                    )
                )
            elif self.AWS_KEY_REGEX.search(str_val) or self.JWT_REGEX.search(str_val) or (self.TOKEN_FIELD_REGEX.search(key_lower) and len(str_val) > 20):
                findings.append(
                    VulnerabilityFinding(
                        title=f"Exposed Auth Secret in MongoDB `{doc.collection_name}.{key}`",
                        category=VulnerabilityCategory.CREDENTIAL_LEAK,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        line_number=doc.line_number,
                        snippet=f'"{key}": "{str_val[:10]}...{str_val[-4:]}"',
                        remediation="Store secrets in a dedicated vault service; avoid persisting raw bearer tokens in document records.",
                        evidence=f"Hardcoded auth token or key in `{doc.collection_name}`.",
                        cwe_id="CWE-798",
                        compliance_tags=["OWASP-A07:2021"],
                    )
                )

            if isinstance(val, dict):
                for k, v in val.items():
                    check_field(f"{key}.{k}", v)

        for field_k, field_v in doc.data.items():
            check_field(field_k, field_v)

        return findings

    def _scan_query(self, query: QueryStatement, file_name: str) -> List[VulnerabilityFinding]:
        findings = []
        q_text = query.query_text
        q_upper = q_text.upper()

        # 1. SQL & SQLite Injections
        if query.dialect in ("SQL", "SQLITE"):
            # Concatenation injection
            concat_patterns = [
                re.compile(r"(['\"][^'\"]*['\"]\s*\+\s*[a-zA-Z_]\w*)"),
                re.compile(r"([a-zA-Z_]\w*\s*\+\s*['\"][^'\"]*['\"])"),
                re.compile(r"(['\"][^'\"]*['\"]\s*\|\|\s*[a-zA-Z_]\w*)"),
                re.compile(r"WHERE\s+\w+\s*=\s*['\"]\s*\+\s*"),
                re.compile(r"WHERE\s+\w+\s*=\s*['\"]?\$[a-zA-Z_]\w*"),
            ]
            for pattern in concat_patterns:
                match = pattern.search(q_text)
                if match:
                    findings.append(
                        VulnerabilityFinding(
                            title="SQL Injection: Dynamic String Concatenation",
                            category=VulnerabilityCategory.SQL_INJECTION,
                            severity=VulnerabilitySeverity.CRITICAL,
                            file_name=file_name,
                            line_number=query.line_number,
                            snippet=q_text[:140],
                            remediation="Use parameterized queries (Prepared Statements with '?' or named parameters) instead of string concatenation.",
                            evidence=f"Dynamic string concatenation detected in query: {match.group(0)}",
                            cwe_id="CWE-89",
                            compliance_tags=["OWASP-A03:2021", "PCI-DSS-Req-6.5"],
                            confidence=0.95,
                        )
                    )
                    break

            # Tautologies / Auth Bypass
            if re.search(r"('\s*OR\s*'1'='1|'\s*OR\s*1=1\s*--|OR\s+'x'='x')", q_text, re.I):
                findings.append(
                    VulnerabilityFinding(
                        title="SQL Injection: Authentication Bypass Tautology",
                        category=VulnerabilityCategory.SQL_INJECTION,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:140],
                        remediation="Rewrite queries to use bound parameterized inputs to neutralize SQL tautologies.",
                        evidence="Tautology signature (' OR '1'='1) detected in query string.",
                        cwe_id="CWE-89",
                        compliance_tags=["OWASP-A03:2021"],
                        confidence=0.99,
                    )
                )

            # Dangerous Stored Procedures / Shell Execution
            if any(proc in q_upper for proc in ("XP_CMDSHELL", "EXECUTE IMMEDIATE", "SP_EXECUTESQL")):
                findings.append(
                    VulnerabilityFinding(
                        title="Critical Stored Procedure Execution (Command Injection Vector)",
                        category=VulnerabilityCategory.SQL_INJECTION,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:120],
                        remediation="Disable `xp_cmdshell` and avoid `EXECUTE IMMEDIATE` with untrusted strings.",
                        evidence="Command execution stored procedure detected in database statements.",
                        cwe_id="CWE-78",
                        compliance_tags=["OWASP-A03:2021"],
                        confidence=0.99,
                    )
                )

            # Blind Time-Based Signatures
            if any(blind in q_upper for blind in ("SLEEP(", "BENCHMARK(", "WAITFOR DELAY", "PG_SLEEP(")):
                findings.append(
                    VulnerabilityFinding(
                        title="Blind SQL Injection Signature Detected",
                        category=VulnerabilityCategory.SQL_INJECTION,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:120],
                        remediation="Isolate database execution and prevent client input from invoking sleep/delay functions.",
                        evidence="Time-delay SQL function detected in query string.",
                        cwe_id="CWE-89",
                        compliance_tags=["OWASP-A03:2021"],
                        confidence=0.95,
                    )
                )

            # Excessive Privileges
            if "GRANT ALL" in q_upper and ("*.*" in q_upper or "ALL PRIVILEGES" in q_upper):
                findings.append(
                    VulnerabilityFinding(
                        title="Insecure Privilege Escalation: GRANT ALL ON *.*",
                        category=VulnerabilityCategory.INSECURE_PRIVILEGE,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:120],
                        remediation="Apply the Principle of Least Privilege (PoLP). Grant only minimum required privileges on designated schemas.",
                        evidence="Overly permissive administrative privileges granted across all tables/databases.",
                        cwe_id="CWE-272",
                        compliance_tags=["OWASP-A01:2021", "PCI-DSS-Req-7.1"],
                        confidence=0.98,
                    )
                )

        # 2. MongoDB NoSQL Injections
        if query.dialect == "MONGO" or "$where" in q_text or "$accumulator" in q_text:
            if "$where" in q_text:
                findings.append(
                    VulnerabilityFinding(
                        title="MongoDB NoSQL Injection: Arbitrary JavaScript Execution via `$where`",
                        category=VulnerabilityCategory.NOSQL_INJECTION,
                        severity=VulnerabilitySeverity.CRITICAL,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:140],
                        remediation="Avoid using `$where` expressions that execute raw JavaScript. Use native MongoDB query operators ($eq, $expr) instead.",
                        evidence="Usage of `$where` operator allows attackers to execute arbitrary server-side JavaScript.",
                        cwe_id="CWE-943",
                        compliance_tags=["OWASP-A03:2021"],
                        confidence=0.99,
                    )
                )
            if "$accumulator" in q_text or "$function" in q_text:
                findings.append(
                    VulnerabilityFinding(
                        title="MongoDB NoSQL Injection: Custom JavaScript Function in Aggregation Pipeline",
                        category=VulnerabilityCategory.NOSQL_INJECTION,
                        severity=VulnerabilitySeverity.HIGH,
                        file_name=file_name,
                        line_number=query.line_number,
                        snippet=q_text[:140],
                        remediation="Disable or restrict custom JavaScript operators (`$accumulator`, `$function`) in production MongoDB instances.",
                        evidence="Arbitrary JavaScript function executed within MongoDB aggregation pipeline.",
                        cwe_id="CWE-943",
                        compliance_tags=["OWASP-A03:2021"],
                        confidence=0.95,
                    )
                )

        return findings

    def _is_modern_hash(self, text: str) -> bool:
        if not text:
            return True
        if self.BCRYPT_REGEX.search(text) or self.ARGON2_REGEX.search(text) or self.PBKDF2_REGEX.search(text):
            return True
        return False

    def _find_credit_card(self, text: str) -> Optional[str]:
        m = self.CC_REGEX.search(text)
        if m:
            return m.group(0)
        m2 = self.CC_DELIM_REGEX.search(text)
        if m2:
            return m2.group(0)
        return None

    def _validate_luhn(self, card_str: str) -> bool:
        if not card_str.isdigit() or not (13 <= len(card_str) <= 19):
            return False
        digits = [int(d) for d in card_str]
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = d * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += d
        return checksum % 10 == 0

    def _mask(self, val: str, keep: int = 2) -> str:
        if len(val) <= keep:
            return "***"
        return val[:keep] + "*" * (len(val) - keep)

    def _mask_card(self, card: str) -> str:
        clean = re.sub(r"[-\s]", "", card)
        if len(clean) >= 12:
            return clean[:4] + "-****-****-" + clean[-4:]
        return "****-****-****"

    def _build_summary(self, parsed_db: ParsedDatabase, findings: List[VulnerabilityFinding]) -> ScanSummary:
        crit = sum(1 for f in findings if f.severity == VulnerabilitySeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == VulnerabilitySeverity.HIGH)
        med = sum(1 for f in findings if f.severity == VulnerabilitySeverity.MEDIUM)
        low = sum(1 for f in findings if f.severity == VulnerabilitySeverity.LOW)

        # Risk score calculation
        raw_score = (crit * 25) + (high * 15) + (med * 8) + (low * 3)
        risk_score = min(100, raw_score)

        # Compliance framework breakdown
        compliance_breakdown: Dict[str, int] = {
            "PCI-DSS": 0,
            "GDPR": 0,
            "HIPAA": 0,
            "OWASP": 0,
        }
        for f in findings:
            for tag in f.compliance_tags:
                tag_upper = tag.upper()
                if "PCI-DSS" in tag_upper:
                    compliance_breakdown["PCI-DSS"] += 1
                if "GDPR" in tag_upper or "CCPA" in tag_upper:
                    compliance_breakdown["GDPR"] += 1
                if "HIPAA" in tag_upper:
                    compliance_breakdown["HIPAA"] += 1
                if "OWASP" in tag_upper:
                    compliance_breakdown["OWASP"] += 1

        total_recs = len(parsed_db.rows) + len(parsed_db.documents)
        total_tables_cols = len(parsed_db.tables) + len(parsed_db.collections)

        return ScanSummary(
            file_name=parsed_db.source_file,
            file_type=parsed_db.file_type,
            total_records=total_recs,
            total_tables_collections=total_tables_cols,
            risk_score=risk_score,
            critical_count=crit,
            high_count=high,
            medium_count=med,
            low_count=low,
            scan_timestamp=datetime.datetime.utcnow().isoformat() + "Z",
            findings=findings,
            compliance_breakdown=compliance_breakdown,
        )
