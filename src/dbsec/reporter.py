"""Audit reporting and compliance generator for dbsec."""
import json
from typing import Dict, Any
from src.dbsec.models import ScanSummary, VulnerabilityFinding


class SecurityReporter:
    """Formats scan results into human-readable or structured security reports."""

    def to_json(self, summary: ScanSummary) -> str:
        return summary.model_dump_json(indent=2)

    def to_dict(self, summary: ScanSummary) -> Dict[str, Any]:
        return summary.model_dump()

    def generate_markdown_report(self, summary: ScanSummary) -> str:
        md = []
        md.append(f"# Database Security Audit Report: {summary.file_name}")
        md.append(f"**Scan Timestamp**: {summary.scan_timestamp}")
        md.append(f"**Database Type**: `{summary.file_type}`")
        md.append(f"**Risk Score**: `{summary.risk_score}/100`")
        md.append(
            f"**Findings Summary**: {summary.critical_count} Critical, {summary.high_count} High, {summary.medium_count} Medium, {summary.low_count} Low"
        )
        if summary.compliance_breakdown:
            compliance_str = ", ".join(f"{k}: {v} violations" for k, v in summary.compliance_breakdown.items() if v > 0)
            if compliance_str:
                md.append(f"**Compliance Violations**: {compliance_str}")

        md.append("\n---\n")

        if not summary.findings:
            md.append("No security vulnerabilities detected. Database conforms to security baselines.")
            return "\n".join(md)

        md.append("## Vulnerability Findings\n")
        for idx, f in enumerate(summary.findings, start=1):
            md.append(f"### {idx}. [{f.severity.value}] {f.title}")
            md.append(f"- **Category**: `{f.category.value}`")
            if f.cwe_id:
                md.append(f"- **CWE**: {f.cwe_id}")
            if f.compliance_tags:
                md.append(f"- **Compliance Standards**: {', '.join(f.compliance_tags)}")
            if f.table_name:
                md.append(f"- **Table / Collection**: `{f.table_name}`")
            if f.line_number:
                md.append(f"- **Record / Line Number**: {f.line_number}")
            md.append(f"- **Evidence**: {f.evidence}")
            md.append(f"- **Vulnerable Snippet**:\n```sql\n{f.snippet}\n```")
            md.append(f"- **Remediation**:\n> {f.remediation}\n")

        return "\n".join(md)
