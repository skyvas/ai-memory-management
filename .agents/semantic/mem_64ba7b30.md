---
id: mem_64ba7b30
type: semantic
scope: project
project_id: dbsec_v1
importance: 0.85
confidence: 0.94
source: pattern_finder
status: active
version: 2
created_at: 2026-09-09T08:27:52.412981Z
metadata: {"reason": "Correlation between SQL and MongoDB security findings reveals storage-agnostic vulnerability patterns."}
---

# Systemic Vulnerability Pattern: Unencrypted sensitive credentials and PII (passw...

Systemic Vulnerability Pattern: Unencrypted sensitive credentials and PII (passwords, credit cards, SSNs) are systemic architectural vulnerabilities across both SQL and NoSQL databases. The tool must enforce unified post-scan compliance checks (PCI-DSS 3.4 and GDPR Article 32) regardless of storage format.
