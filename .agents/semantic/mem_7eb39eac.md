---
id: mem_7eb39eac
type: semantic
scope: project
project_id: dbsec_v1
importance: 0.85
confidence: 0.95
source: pattern_finder
status: active
version: 2
created_at: 2026-09-09T08:27:52.412995Z
metadata: {"reason": "Synthesized common root cause for SQL and NoSQL injection vulnerabilities."}
---

# Architectural Insight: Query injection vectors occur wherever user input is eval...

Architectural Insight: Query injection vectors occur wherever user input is evaluated dynamically—whether via SQL string concatenation or MongoDB server-side JavaScript ($where). Remediation requires structural separation of code and data across all database interaction layers.
