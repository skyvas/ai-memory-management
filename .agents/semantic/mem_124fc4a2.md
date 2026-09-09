---
id: mem_124fc4a2
type: semantic
scope: project
project_id: dbsec_v1
importance: 0.85
confidence: 0.95
source: pattern_finder
status: active
version: 4
created_at: 2026-09-09T09:43:28.476043Z
metadata: {"reason": "Synthesized common root cause for SQL and NoSQL injection vulnerabilities."}
---

# Architectural Insight: Query injection vectors occur wherever user input is eval...

Architectural Insight: Query injection vectors occur wherever user input is evaluated dynamically—whether via SQL string concatenation or MongoDB server-side JavaScript ($where). Remediation requires structural separation of code and data across all database interaction layers.
