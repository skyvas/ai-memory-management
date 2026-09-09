---
id: mem_e4f7237c
type: semantic
scope: project
project_id: dbsec_v1
importance: 0.85
confidence: 0.96
source: pattern_finder
status: active
version: 8
created_at: 2026-09-09T10:56:54.408828Z
metadata: {"reason": "Synthesized common root cause for SQL and NoSQL injection vulnerabilities into scanner guidance.", "topic_file": "scanner-rules.md"}
---

# Architectural Insight: Query injection vectors occur wherever user input is eval...

Architectural Insight: Query injection vectors occur wherever user input is evaluated dynamically—whether via SQL string concatenation or MongoDB server-side JavaScript ($where). Remediation requires structural separation of code and data across all database interaction layers.
