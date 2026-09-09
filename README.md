Dreaming Multi-Agent Memory System
Overview
This document describes a memory-efficient AI-supported multi-agent
 architecture built around a dreaming process. The central idea is:
 agents generate experience, memory stores experience, and dreaming
 turns experience into knowledge.
1. System Modes
The system has two major modes:
	●	Waking mode: the orchestrator routes tasks to specialized
 agents. Agents retrieve only relevant memories and create new
 memories from useful experience.
	●	Dreaming mode: an asynchronous process works on a snapshot of
 long-term memory to consolidate, compress, reorganize, connect, and
 evaluate knowledge.
Dreaming is an engineering metaphor for offline memory consolidation
 rather than a claim about consciousness.
2. High-Level Architecture
```text
 User / Events
       |
       v
 Agent Orchestrator
       |
   +---+---+---+
   |       |       |
 Research Coding Planning
   |       |       |
   +-------+-------+
           |
           v
     Memory Manager
           |
    +------+------+
    |             |
 Working      Long-Term
 Memory        Memory
                  |
                  v
           SQL + Vector Index
                  |
               Snapshot
                  |
                  v
          Dream Orchestrator
                  |
        +---------+---------+
        |         |         |
 Consolidator Pattern  Contradiction
               Finder      Resolver
        |         |         |
        +---------+---------+
                  |
                  v
               Evaluator
                  |
           Accept / Reject
                  |
                  v
        Consolidated Version
 ```
3. Waking Mode
Waking mode is the normal operational state. A user request reaches the
 orchestrator, which decides which agents should work on it. Each agent
 receives the task plus a small, relevant subset of memory.
The key rule is: shared memory does not mean shared context.
 Multiple agents can access the same memory system without receiving the
 entire history.
Instead of passing 100,000 tokens of conversation history to every
 agent, the system performs retrieval and supplies perhaps 5–20 relevant
 memories.
4. Agent Architecture
Agents should remain independent of the storage implementation. A
 conceptual interface is:
```python
 class Agent:
     name: str

     def run(self, task, context):
         ...
 ```
Agents should use a Memory Manager rather than directly accessing
 database tables or vector indexes. This allows the storage and retrieval
 implementation to evolve without rewriting agents.
5. Memory Manager
A central memory abstraction can expose operations such as:
```text
 remember()
 recall()
 search()
 update()
 merge()
 forget()
 archive()
 link()
 snapshot()
 restore()
 ```
The Memory Manager owns policies for admission, retrieval,
 consolidation, scope, and lifecycle.
6. Memory Types
Working memory
Contains current conversation state, active tasks, temporary reasoning
 results, and intermediate tool outputs. It is small, fast, and
 short-lived.
Episodic memory
Stores significant events and interactions: what happened, when it
 happened, and where it came from.
Semantic memory
Stores durable knowledge extracted from experience: facts, decisions,
 concepts, constraints, patterns, and relationships.
Shared project state
Stores information that multiple agents need to coordinate around, such
 as technology choices, project status, milestones, and current
 objectives.
7. Memory Scope
Every memory should have an explicit scope. A useful hierarchy is:
```text
 User
   └── Project
        └── Task
             └── Agent
 ```
Possible scopes include global, user, project, task, session, agent, and
 temporary. Scope prevents temporary reasoning from accidentally becoming
 global knowledge.
Example:
```json
 {
   "content": "Use Python 3.13 for the backend.",
   "scope": "project",
   "project_id": "proj_123",
   "importance": 0.9,
   "confidence": 0.95
 }
 ```
8. Memory Admission
Not every conversation statement deserves permanent storage. A
 memory-admission pipeline should be:
```text
 Interaction
    -> Candidate information
    -> Importance filter
    -> Deduplication
    -> Compression / summarization
    -> Classification
    -> Storage
 ```
Useful admission signals include importance, durability, confidence,
 recurrence, novelty, future usefulness, user relevance, project
 relevance, and source reliability.
For example, “Okay, let’s continue” is unlikely to be valuable long-term
 memory, while “The project uses PostgreSQL as its primary database” is
 likely to be valuable.
9. Memory Representation
A memory record can contain:
```json
 {
   "id": "mem_123",
   "type": "fact",
   "content": "The project uses PostgreSQL as its primary database.",
   "scope": "project",
   "project_id": "proj_123",
   "importance": 0.85,
   "confidence": 0.95,
   "source": "research_agent",
   "status": "active"
 }
 ```
Additional metadata can include source session, source agent, evidence
 count, last accessed time, last confirmed time, expiration, version,
 parent memory, related memories, and embedding.
10. Hybrid Retrieval
Retrieval should combine semantic search with structured information.
```text
 Query
   |
   +--> Semantic search
   |
   +--> Structured / metadata search
           |
           v
        Re-ranker
           |
           v
   Top relevant memories
 ```
Signals can include semantic similarity, exact matching, scope, recency,
 importance, confidence, access frequency, and relationship proximity.
11. The Dreaming Concept
Dreaming is an asynchronous memory-processing phase. It periodically
 asks:
> What should be kept, merged, compressed, connected, corrected,
 > archived, or forgotten?
The lifecycle becomes:
```text
 Experience -> Remember -> Retrieve -> Dream -> Consolidate -> Forget -> Remember better
 ```
12. Memory Snapshot
Dreaming should operate on a copy or versioned snapshot rather than
 directly modifying live memory.
```text
 LIVE MEMORY
     |
     +--> Waking agents continue working
     |
     +--> Snapshot --> DREAM MEMORY
                          |
                          +--> experiment
                          +--> consolidate
                          +--> evaluate
 ```
If a dream produces poor changes, production memory remains protected.
13. Dream Orchestrator
The normal orchestrator asks, “What should the system do now?” The Dream
 Orchestrator asks, “What should the system learn or change about its
 memory?”
It coordinates specialized dream agents and sends their proposals to an
 evaluator.
14. Dream Agent Roles
Consolidator
Finds duplicate or equivalent memories and merges them.
Example:
```text
 “We use PostgreSQL.”
 “Backend database is PostgreSQL.”
 “Our primary DB is Postgres.”
         |
         v
 “The project uses PostgreSQL as its primary database.”
 ```
Pattern Finder
Searches across sessions and agents for recurring patterns that can
 become higher-level knowledge.
Contradiction Resolver
Finds conflicting memories and evaluates timestamps, evidence, source
 reliability, subsequent decisions, and project state. Historical
 information can be preserved while obsolete information is marked
 inactive.
Memory Compressor
Reduces many repetitive fragments into a smaller set of useful memories
 while preserving meaning, evidence, provenance, and temporal
 information.
Relationship Builder
Builds connections such as uses, depends_on, replaces,
 contradicts, supports, derived_from, related_to, and part_of.
 This moves memory toward a knowledge graph.
15. Dream Proposals
Dream agents should normally propose changes rather than directly
 committing them. Proposal operations can include:
```text
 CREATE
 UPDATE
 MERGE
 DELETE
 ARCHIVE
 LINK
 RECLASSIFY
 CHANGE_SCOPE
 CHANGE_CONFIDENCE
 ```
Example:
```json
 {
   "operation": "merge",
   "memories": ["mem_101", "mem_203", "mem_404"],
   "result": "The project uses PostgreSQL as its primary database.",
   "confidence": 0.94,
   "reason": "Three independent memories contain equivalent information."
 }
 ```
16. Dream Evaluator
The evaluator determines whether proposed changes are safe and useful.
 Possible scoring dimensions are confidence, importance, recency,
 evidence, source reliability, supporting-session count, contradiction
 level, and future usefulness.
The principle is:
> Dream agents propose; an evaluation layer decides.
17. Memory Versioning
Memory should be versioned rather than treated as one untraceable
 mutable object.
```text
 Memory v17
     |
     +--> Dream cycle
             |
             +--> Memory v18
 ```
Versioning enables auditing, experimentation, comparison, rollback, and
 debugging.
18. Forgetting and Archiving
A memory-efficient system needs forgetting. A safer lifecycle is often:
```text
 active -> stale -> archived -> deleted
 ```
Archiving removes low-value information from normal retrieval while
 preserving it for historical reconstruction when appropriate.
19. Memory Decay
Memory activity can depend on age, access frequency, importance,
 confirmation, project status, relevance, and expiration. Dreaming is a
 natural place to evaluate which memories should remain active.
20. Cross-Agent Learning
Different agents can discover different pieces of a larger insight. For
 example:
```text
 Research Agent: technology constraint
 Coding Agent: implementation limitation
 Planning Agent: deadline
              |
              v
        Dreaming process
              |
              v
      Higher-level project insight
 ```
Dreaming therefore becomes a mechanism for integrating knowledge that no
 individual agent explicitly discovered.
21. Dream Workspace
A dream workspace can contain a temporary memory clone plus candidate
 memories, summaries, proposals, relationships, hypotheses, and
 evaluation results. It can be discarded after promotion or rollback.
22. Hypothesis Generation
Dream agents can generate hypotheses from repeated observations. A
 hypothesis should remain separate from confirmed knowledge until
 sufficient evidence exists.
Example:
```text
 Observation 1: Several tasks depend on PostgreSQL.
 Observation 2: Multiple agents query database architecture.
                  |
                  v
 Hypothesis: Database architecture should be a first-class project memory.
 ```
23. Safety and Bounded Autonomy
Dreaming should be bounded by explicit memory operations. It should
 primarily modify memory, metadata, relationships, summaries, and
 knowledge structures. External side effects should require separate
 authorization.
24. Validation
Before promoting a dream version, validate:
	●	Integrity: references remain valid.
	●	Consistency: contradictions are reduced rather than introduced.
	●	Compression: redundant information is actually reduced.
	●	Retrieval quality: important memories remain discoverable.
	●	Provenance: important new memories can be traced to evidence.
	●	Regression: useful knowledge was not accidentally lost.
25. Storage Architecture
A practical initial storage design is:
```text
 Memory API
    |
    +--> PostgreSQL: durable source of truth
    |
    +--> pgvector: semantic retrieval index
    |
    +--> Optional Redis: working memory / cache / queues
 ```
PostgreSQL should hold durable memory records, metadata, relationships,
 sessions, agents, versions, proposals, and audit records. pgvector can
 provide embedding-based retrieval. Redis is optional for short-lived
 state and caching.
26. Conceptual Data Model
```text
 users
   |
   +--> projects
         |
         +--> sessions
         +--> agents
         +--> memories
               |
               +--> memory_versions
               +--> memory_links
               +--> memory_evidence

 dream_runs
   |
   +--> dream_agents
   +--> dream_proposals
   +--> evaluations
   +--> promoted_changes
 ```
27. Evidence and Provenance
A durable memory should be able to answer: Why do we believe this?
For example:
```text
 Memory: The project uses PostgreSQL.
 Evidence:
   - Session 17
   - Session 21
   - Architecture decision #4
 ```
Provenance is especially important when resolving contradictions and
 reassessing memories during future dream cycles.
28. Confidence and Importance
Confidence and importance should be separate dimensions. A fact can be
 highly certain but unimportant, or highly important but uncertain.
 Dreaming can use both dimensions when deciding what to promote,
 retrieve, or archive.
29. Shared Memory vs Shared Context
Multiple agents can share a memory system without sharing the same LLM
 context. Each agent retrieves the subset relevant to its current task.
 This is one of the main mechanisms for preventing context growth.
30. End-to-End Example
A project may evolve like this:
```text
 Day 1: Research Agent -> PostgreSQL is a candidate.
 Day 2: Coding Agent  -> Prototype uses PostgreSQL.
 Day 5: Planning Agent -> Production architecture uses PostgreSQL.
               |
               v
          Dream cycle
               |
               v
 Consolidated memory: Project uses PostgreSQL as primary database.
 ```
The system can preserve the historical observations while making the
 consolidated fact the active semantic memory.
31. Recommended Version 1 Architecture
Start with:
```text
 User
  |
 v
 Orchestrator
  |
 +--> Research Agent
 +--> Coding Agent
 +--> Planning Agent
  |
 v
 Memory Manager
  |
 v
 PostgreSQL + pgvector
  |
 snapshot
 v
 Dream Orchestrator
  |
 +--> Consolidator
 +--> Pattern Finder
 +--> Contradiction Resolver
  |
 v
 Evaluator
  |
 Accept / Reject
  |
 v
 New Memory Version
 ```
The MVP should remain simple. The important thing is to prove the memory
 lifecycle before adding sophisticated infrastructure.
32. Development Roadmap
Phase 1 — Basic Memory
Implement agents, Memory Manager, PostgreSQL, pgvector, remember(),
 and recall().
Phase 2 — Memory Admission
Add importance, confidence, scope, type, and provenance. Establish rules
 for what becomes persistent memory.
Phase 3 — Consolidation
Build the first Dream Agent for duplicate detection, merging, and
 summarization.
Phase 4 — Evaluation and Versioning
Add dream proposals, an evaluator, memory versions, validation, and
 rollback.
Phase 5 — Multiple Dream Agents
Add pattern discovery, contradiction resolution, compression, and
 relationship building.
Phase 6 — Advanced Knowledge
Introduce knowledge graphs, temporal memory, decay, hypothesis
 generation, and deeper cross-agent learning.
33. Suggested API Surface
A possible API is:
```text
 POST  /memory
 GET   /memory/search
 GET   /memory/{id}
 PATCH /memory/{id}
 POST  /memory/{id}/archive

 POST  /dream/run
 GET   /dream/{id}
 GET   /dream/{id}/proposals
 POST  /dream/{id}/evaluate
 POST  /dream/{id}/promote

 GET   /memory/versions
 POST  /memory/versions/{id}/restore
 ```
34. Observability
Record:
	●	which memories were retrieved
	●	which memories were created
	●	which memories were updated
	●	which dream agents proposed changes
	●	why proposals were accepted or rejected
	●	which memory version was promoted
	●	which evidence supported a change
A memory system without observability can become difficult to trust and
 debug.
35. Why This Is More Than a Vector Database
A vector database primarily answers:
> What stored text is semantically similar to this query?
A true memory system needs to answer richer questions:
```text
 What do we know?
 Why do we know it?
 When did we learn it?
 Who learned it?
 Is it still valid?
 What supports it?
 What contradicts it?
 What is it related to?
 How important is it?
 Should it be remembered?
 Should it be forgotten?
 ```
Vector search is therefore one component of the larger memory
 architecture.
36. The Core Feedback Loop
The mature system forms a continuous feedback loop:
```text
 User
   |
   v
 Experience
   |
   v
 Agent Work
   |
   v
 Memory
   |
   v
 Retrieve
   |
   v
 Better Work
   |
   v
 Memory
   |
   v
 Dream
   |
   v
 Better Memory Model
   |
   +------> Waking Agents
 ```
37. Final Mental Model
The architecture can be reduced to three concepts:
```text
                 WAKING
                   |
           Agents solve tasks
                   |
                   v
              EXPERIENCE
                   |
                   v
           LONG-TERM MEMORY
                   |
              periodically
                   v
               DREAMING
                   |
        +----------+----------+
        |          |          |
   Consolidate  Discover   Resolve
        |       Patterns   Conflicts
        +----------+----------+
                   |
                   v
           BETTER MEMORY MODEL
                   |
                   v
           WAKING AGENTS
 ```
The central philosophy is:
> **Waking agents generate experience. Memory preserves useful
 > experience. Dreaming reorganizes experience into durable knowledge.
 > Retrieval gives each agent only the knowledge it needs. Evaluation
 > prevents uncontrolled memory changes. Versioning makes the process
 > reversible and auditable.**
This creates a foundation for a memory-efficient multi-agent AI system
 that can grow in capability without requiring every agent to carry the
 complete history of the system in its context.

