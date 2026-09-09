# Scanner Rules

- Architectural Insight: Query injection vectors occur wherever user input is evaluated dynamically—whether via SQL string concatenation or MongoDB server-side JavaScript ($where). Remediation requires structural separation of code and data across all database interaction layers.
