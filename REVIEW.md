# EverCurrent — Principal Engineer Design & Implementation Review (v2)

**Review Panel:**
- Principal Software Engineer, Slack (distributed systems, API design, real-time pipelines, DX)
- Principal AI Engineer, Google (LLM pipelines, prompt engineering, evaluation, ML systems)
- Principal Frontend Engineer, Google (React, TypeScript, design systems, accessibility, performance)
- Principal Product Engineer, Stripe (persona modeling, feedback loops, adoption, information hierarchy)
- Senior Staff Hardware Engineer, Boston Dynamics (phase-gate processes, EVT/DVT/PVT, cross-discipline failure modes)
- All hold dual PhDs in CS and Mathematics from Oxford

**Date:** 2026-03-31
**Codebase Snapshot:** commit `f67a824` (63 beads issues closed, 411 tests, 99% coverage)

---

## Overall Grade: A-

This is a remarkably well-executed prototype. The five-layer pipeline is thoughtfully designed, the domain modeling is sophisticated, and the engineering discipline (99% coverage, 7 quality gates) is exceptional. But there's one strategic gap that could transform this from "impressive prototype" to "this person understands our product": **EverCurrent's most critical component is a knowledge graph, and this prototype doesn't have one.**

Ye Wang described EverCurrent as a system that *tracks changes rather than current state* — answering questions like "What are the top 5 changes affecting the schedule in the last 7 days?" The current architecture extracts atoms, scores them, generates a digest, and **discards everything**. No memory across runs. No temporal queries. No accumulated knowledge. The (atom, persona) pairs are scored on-the-fly and thrown away.

The review below identifies **4 high-severity recommendations** that, taken together, would align this prototype with EverCurrent's actual product vision. Everything else is grouped as "Next Steps" work.

---

## Table of Contents

1. [Architecture & System Design](#1-architecture--system-design)
2. [Domain Modeling & Data Design](#2-domain-modeling--data-design)
3. [LLM Pipeline Architecture](#3-llm-pipeline-architecture)
4. [Scoring Engine](#4-scoring-engine)
5. [Configuration & Dependency Management](#5-configuration--dependency-management)
6. [Testing Strategy](#6-testing-strategy)
7. [Frontend](#7-frontend)
8. [On LangGraph](#8-on-langgraph)
9. [Critical Recommendations (Do Now)](#9-critical-recommendations-do-now)
10. [Next Steps (Future Work)](#10-next-steps-future-work)
11. [Conclusion](#11-conclusion)

---

## 1. Architecture & System Design

### What Works Well

**Five-layer pipeline with clear boundaries.** Each layer (Ingestion → Extraction → Context → Scoring → Generation) has a single responsibility, a well-defined interface, and can be tested independently.

**Phase-as-vector, not scalar.** Modeling development phase per-workstream rather than per-project is the kind of domain insight that separates toy prototypes from systems that hardware teams would actually use. At Boston Dynamics, chassis DVT and firmware EVT running concurrently is the norm, not the exception.

**Relational relevance model.** The core insight — that relevance is `f(atom, persona)` not `f(atom)` — is correct and well-implemented.

### Issues

#### 1.1 The Pipeline Is Not Wired Together (Severity: Critical)

`/pipeline/run` returns `{"status": "stub"}`. `/digest/{persona_id}` returns empty sections. `DigestAssembler` exists but is not called from any endpoint. The five layers are built and tested in isolation but never composed.

**Impact:** You cannot demo the system doing its primary job.

#### 1.2 No Persistent Knowledge — Stateless Batch Architecture (Severity: Critical)

This is the strategic gap. Everything lives in memory and is recomputed every request. Atoms, scores, digests — all ephemeral. The architecture can produce "here's your digest" but cannot answer:
- "What changed since yesterday?"
- "What are the top 5 changes affecting the schedule this week?"
- "Has this spec changed before? How many times?"
- "Is this blocker a pattern or a one-off?"

These are the questions Ye Wang described as EverCurrent's core value proposition. The system needs a **persistent knowledge graph** — not a database table, but a graph of interconnected entities with typed, timestamped edges that accumulate over time.

#### 1.3 Module-Level Config Loading Creates Hidden Coupling (Severity: Medium)

Multiple modules execute `get_config()` at import time, freezing config at import time with no way to reload.

#### 1.4 No Async in the Pipeline (Severity: Medium)

FastAPI endpoints are `async def` but the entire pipeline is synchronous. LLM calls process windows sequentially — 50+ serial round-trips at ~2s each.

---

## 2. Domain Modeling & Data Design

### What Works Well

**Pydantic models are well-structured.** `Atom`, `Persona`, `Digest` — frozen where appropriate, validated at boundaries, with sensible defaults.

**The `Atom` model captures real hardware engineering information.** The eight atom types (DECISION, SPEC_CHANGE, ACTION_ITEM, BLOCKER, RISK, TEST_RESULT, STATUS_UPDATE, QUESTION) map directly to what actually matters in phase-gate hardware development.

### Issues

#### 2.1 `ScoringWeights` Doesn't Enforce Sum-to-One (Severity: Medium)

Nothing prevents `ScoringWeights(workstream_proximity=5.0, ...)`, which produces composite scores > 1.0. Add a Pydantic `model_validator` that asserts `math.isclose(total, 1.0)`.

#### 2.2 Atom Provenance Is Fragile (Severity: Low)

`AtomSource.message_range` is `list[int]` with min/max constraints. Should be a dedicated `Range` type. LLM-generated indices are never validated against actual messages.

#### 2.3 No Atom Deduplication After Extraction (Severity: Medium)

The `filter.py` mentions "duplicate detection" but only does confidence filtering. Overlapping context windows can produce duplicate atoms that both survive into scoring.

---

## 3. LLM Pipeline Architecture

### What Works Well

**The LLMClient Protocol pattern is clean.** Provider-agnostic interface, adapter pattern for each SDK, factory with lazy imports.

**Extraction prompt is well-engineered.** The three critical rules (extract conclusions not discussions, flag implicit decisions, tag cross-workstream impact) encode genuine domain expertise.

**Two-pass validation for DECISION/SPEC_CHANGE.** Second LLM call for high-stakes atoms is the right engineering decision.

### Issues

#### 3.1 No Structured Output Enforcement (Severity: High)

Both extraction and generation rely on `json.loads()` as the only parse step. When the LLM returns markdown-fenced JSON or adds explanatory text, the pipeline **silently drops the entire response**:

```python
try:
    data = json.loads(raw_text)
except json.JSONDecodeError:
    logger.warning("Failed to parse JSON response: %s...", raw_text[:100])
    return []  # Silent data loss
```

**This is the #1 production ML engineering concern.** Every major LLM occasionally returns non-JSON responses. Silent data loss is unacceptable.

#### 3.2 Prompt Cognitive Overload (Severity: Medium)

The 88-line extraction prompt asks the LLM to extract, classify, assign confidence, identify participants, tag workstreams, determine urgency, assess phase relevance, and detect implicit decisions — all in one pass.

#### 3.3 No Token Counting or Cost Tracking (Severity: Medium)

No visibility into token usage or cost for a system that makes dozens of LLM calls per pipeline run.

#### 3.4 Validation Prompt Leaks Metadata (Severity: Low)

`_validate_single` sends the full `atom.model_dump_json()` to the validator, including the confidence score and atom_id, potentially biasing the second-pass judgment.

---

## 4. Scoring Engine

### What Works Well

**Five independent, composable dimensions.** Each scorer is a pure function `f(atom, persona) -> float ∈ [0,1]`.

**Config-driven matrices.** The role-alignment and phase-alignment matrices live in YAML, not code.

**Critical threshold overflow.** Ensuring high-urgency items appear even beyond `max_items` is the right UX decision.

### Issues

#### 4.1 Scoring Is Not Calibrated (Severity: Medium)

The five dimensions have different distributions (discrete 4-value vs continuous). The relative influence of each dimension doesn't match the stated weights. Urgency and social signal have 0.3-0.5 step sizes that dominate ranking decisions.

#### 4.2 Phase Alignment Is Binary (Severity: Medium)

No concept of "adjacent phase relevance" — DVT→PVT (one phase away) scores the same as Concept→MP (four phases away). Should score by phase distance.

#### 4.3 Social Signal Is Flat (Severity: Low)

The collaborator graph is a flat adjacency list. No transitivity — if Maya collaborates with Li, and Li collaborates with the atom author, that's a signal the system misses.

---

## 5. Configuration & Dependency Management

### What Works Well

**YAML-driven configuration.** Five config files cleanly separate concerns.

**Optional LLM providers as extras** with lazy imports is the right pattern.

### Issues

#### 5.1 Global Mutable State in Config Loader (Severity: Medium)

Module-level singleton with no invalidation or thread safety.

#### 5.2 `anthropic` Is a Hard Dependency (Severity: Medium)

OpenAI and Google are optional extras, but `anthropic` is unconditionally imported and required. Should be optional like the others.

#### 5.3 `pyyaml` Is Unlisted (Severity: Low)

`import yaml` works transitively but isn't declared in `pyproject.toml`.

---

## 6. Testing Strategy

### What Works Well

**99% coverage with 411 tests.** Exceptional for a prototype.

**Evaluation criteria as tests.** The `test_evaluation/` directory encodes the three success criteria as executable tests.

### Issues

#### 6.1 No Integration Tests (Severity: High)

Every test mocks the LLM. Zero tests exercise the actual API. The system has not been proven to work end-to-end with real LLM responses.

#### 6.2 Tests Over-Specified on Implementation (Severity: Low)

Some tests assert on mock call counts rather than behavioral outcomes, making them brittle to refactoring.

---

## 7. Frontend

### What Works Well

Clean component architecture. TypeScript types mirror backend models.

### Issues

- No error boundaries (network/JSON errors crash the React tree)
- No retry, timeout, or AbortController on API calls
- Hard-coded persona list instead of fetching from API
- No accessibility audit (ARIA, keyboard nav, contrast)

---

## 8. On LangGraph

**Don't adopt LangGraph for this prototype.** Your current architecture is cleaner, more transparent, and easier to debug. The five-layer pipeline is a straightforward DAG — you don't need a framework to manage it.

**Do adopt it when:** you add dynamic routing, human-in-the-loop review, multi-model routing, or streaming partial digests. That's v2+ territory.

The better near-term investment is the knowledge graph and temporal layer described below — which is simpler and more aligned with EverCurrent's product than a workflow framework.

---

## 9. Critical Recommendations (Do Now)

These are the 4 changes that would transform this prototype from "impressive engineering exercise" to "this person understands what we're building." They should be done before the follow-up meeting.

---

### CR-1: Wire the Pipeline End-to-End

**Why this is critical:** Without a working end-to-end demo, the system doesn't do its primary job. Every other improvement is irrelevant if you can't show atoms being extracted, scored, and rendered as personalized digests.

**What to do:**
1. Connect `/digest/{persona_id}` to the real pipeline: Ingestion → Extraction → Scoring → Generation
2. The `DigestAssembler` already exists — call it from the endpoint
3. Wire `/pipeline/run` to trigger extraction and store results

```python
# app.py — wire the assembler
@app.get("/digest/{persona_id}")
async def get_digest(persona_id: str, phase_override: str | None = None):
    assembler = DigestAssembler(create_llm_client())
    atoms = run_extraction_pipeline()  # Layers 1-2
    return assembler.assemble(persona_id, atoms, phase_override)
```

**Effort:** Medium (1-2 hours). Most code already exists.

---

### CR-2: Add a Persistent Knowledge Graph Layer

**Why this is critical:** Ye Wang explicitly identified the **knowledge graph as EverCurrent's most critical component**. He described the system as "tracking changes rather than current state" and answering questions like "What are the top 5 changes affecting the schedule in the last 7 days?" The current architecture cannot do this — atoms are ephemeral, scored and discarded.

Adding a knowledge graph transforms the system from a stateless batch processor into something that **accumulates understanding over time** — the core product vision.

**What the graph looks like:**

```
                  ORIGINATED_IN
            ┌─────────────────────────► Workstream ◄──── WORKS_ON ───── Persona
            │                               │                              │
            │                          CURRENTLY_IN                  COLLABORATES_WITH
            │                               │                              │
            │                               ▼                              ▼
   Atom ────┤                            Phase                          Persona
            │
            ├── AFFECTS ──────────────► Workstream  (cross-team impact)
            │
            ├── SUPERSEDES ───────────► Atom        (temporal chain: spec v2 → v1)
            │
            ├── BLOCKS ───────────────► Atom        (dependency tracking)
            │
            ├── AUTHORED_BY ──────────► Persona     (provenance)
            │
            └── RELEVANT_TO ──────────► Phase       (phase tagging)
```

**Node types:**
| Node | Source | Persistence |
|------|--------|-------------|
| Atom | LLM extraction | Accumulated across pipeline runs |
| Persona | Config/roster | Stable, slow-changing |
| Workstream | Config | Stable |
| Phase | Config + overrides | Mutable (per PhaseVector) |

**Edge types (all timestamped):**
| Edge | From → To | Purpose |
|------|-----------|---------|
| ORIGINATED_IN | Atom → Workstream | Source provenance |
| AFFECTS | Atom → Workstream | Cross-team impact (buried signal) |
| SUPERSEDES | Atom → Atom | Temporal chain — new spec replaces old |
| BLOCKS | Atom → Atom | Blockers reference what they block |
| RELATES_TO | Atom → Atom | Semantic similarity (embedding-based) |
| AUTHORED_BY | Atom → Persona | Key participants |
| RELEVANT_TO | Atom → Phase | Phase tagging |
| WORKS_ON | Persona → Workstream | Weighted affinity |
| COLLABORATES_WITH | Persona → Persona | Social graph |
| CURRENTLY_IN | Workstream → Phase | Phase vector |

**What this enables:**

1. **Temporal queries** — "What changed in chassis since yesterday?"
   ```python
   graph.query(
       node_type="Atom",
       edges={"ORIGINATED_IN": "chassis"},
       since=yesterday
   )
   ```

2. **Change tracking** — New atoms SUPERSEDE old ones. "Spec changed from aluminum to magnesium" links to the original aluminum decision. You get a **change history**, not just a snapshot.

3. **Transitive impact detection** — A chassis SPEC_CHANGE that AFFECTS thermal, combined with thermal AFFECTS supply-chain, creates a 2-hop path that surfaces to supply chain engineers. The current flat scoring misses this.

4. **Pattern detection** — "3 BLOCKERs in chassis DVT in 48 hours = systemic risk" emerges from graph queries, not from individual atom scoring.

5. **Graph-enhanced scoring** — Replace or augment the flat weighted sum with graph centrality. An atom that AFFECTS 4 workstreams and BLOCKS 2 other atoms is inherently more important than one that's isolated — regardless of urgency tags.

**Realistic implementation for the take-home:**

```python
# src/evercurrent/knowledge/graph.py
import networkx as nx
from datetime import datetime
from evercurrent.models.atom import Atom

class KnowledgeGraph:
    """In-memory knowledge graph backed by networkx.
    
    Accumulates atoms across pipeline runs with typed, timestamped edges.
    Supports temporal queries and change tracking.
    """
    
    def __init__(self) -> None:
        self._graph = nx.MultiDiGraph()
    
    def ingest_atom(self, atom: Atom, timestamp: datetime | None = None) -> None:
        """Add an atom and its edges to the graph."""
        ts = timestamp or datetime.now(tz=UTC)
        
        # Add atom node
        self._graph.add_node(
            str(atom.atom_id),
            type="atom",
            atom=atom,
            ingested_at=ts,
        )
        
        # ORIGINATED_IN edge
        self._graph.add_edge(
            str(atom.atom_id),
            f"ws:{atom.workstreams.originating}",
            edge_type="ORIGINATED_IN",
            timestamp=ts,
        )
        
        # AFFECTS edges (cross-team signals)
        for ws in atom.workstreams.affected:
            self._graph.add_edge(
                str(atom.atom_id),
                f"ws:{ws}",
                edge_type="AFFECTS",
                timestamp=ts,
            )
        
        # AUTHORED_BY edges
        for participant in atom.source.key_participants:
            self._graph.add_edge(
                str(atom.atom_id),
                f"persona:{participant}",
                edge_type="AUTHORED_BY",
                timestamp=ts,
            )
        
        # Check for SUPERSEDES (same type + workstream, newer)
        self._detect_supersedes(atom, ts)
    
    def changes_since(
        self,
        workstream: str,
        since: datetime,
    ) -> list[Atom]:
        """Temporal query: what atoms appeared in this workstream since a given time?"""
        results = []
        ws_node = f"ws:{workstream}"
        if ws_node not in self._graph:
            return results
        for predecessor in self._graph.predecessors(ws_node):
            node = self._graph.nodes[predecessor]
            if node.get("type") == "atom" and node["ingested_at"] >= since:
                results.append(node["atom"])
        return sorted(results, key=lambda a: a.urgency, reverse=True)
    
    def impact_radius(self, atom_id: str, hops: int = 2) -> set[str]:
        """Find all workstreams within N hops of an atom."""
        affected = set()
        visited = set()
        frontier = {atom_id}
        for _ in range(hops):
            next_frontier = set()
            for node in frontier:
                if node in visited:
                    continue
                visited.add(node)
                for _, target, data in self._graph.edges(node, data=True):
                    if target.startswith("ws:"):
                        affected.add(target.removeprefix("ws:"))
                    next_frontier.add(target)
            frontier = next_frontier
        return affected
    
    def save(self, path: str) -> None:
        """Persist graph to disk (JSON adjacency format)."""
        # networkx supports JSON serialization
        ...
    
    def load(self, path: str) -> None:
        """Load graph from disk."""
        ...
```

**Integration with existing scoring:**

The knowledge graph doesn't replace the 5-dimension scorer — it enhances it with a 6th dimension: **graph centrality**. Atoms that are connected to more workstreams, supersede more history, or block more work get a graph importance boost.

```python
def score_graph_importance(atom: Atom, graph: KnowledgeGraph) -> float:
    """Score atom importance based on graph connectivity."""
    affected_ws = graph.impact_radius(str(atom.atom_id), hops=2)
    supersedes = graph.supersedes_count(str(atom.atom_id))
    blocks = graph.blocks_count(str(atom.atom_id))
    
    # Normalize to [0, 1]
    ws_factor = min(len(affected_ws) / 5, 1.0)       # 5+ workstreams = max
    history_factor = min(supersedes / 3, 1.0)          # 3+ supersedes = max
    blocking_factor = min(blocks / 2, 1.0)             # 2+ blocks = max
    
    return 0.5 * ws_factor + 0.3 * history_factor + 0.2 * blocking_factor
```

**Effort:** Medium-Large (3-4 hours). networkx handles the graph ops. The main work is wiring it into the pipeline and writing the edge detection logic.

**Why this matters for the interview:** This is the single strongest signal you can send that you understand EverCurrent's product. Every other candidate will build a batch pipeline. Showing a knowledge graph that accumulates understanding over time — even a lightweight one — demonstrates that you read between the lines of the conversation with Ye Wang and aligned your technical choices with the company's core architecture.

---

### CR-3: Add Structured LLM Outputs + JSON Recovery

**Why this is critical:** This is the difference between "works in unit tests with mocked LLM responses" and "works in production with real LLMs." Silent data loss on JSON parse failure is disqualifying at the principal level.

**What to do:**
1. **Use provider structured output modes** — Anthropic supports `tool_use` with JSON schema. OpenAI has `response_format: { type: "json_object" }`. These guarantee valid JSON at the API level.
2. **Add markdown fence stripping** as a fallback:
   ```python
   def _extract_json(text: str) -> str:
       text = text.strip()
       if text.startswith("```"):
           text = re.sub(r"^```\w*\n?", "", text)
           text = re.sub(r"\n?```$", "", text)
       return text
   ```
3. **Add retry with backoff** on parse failure instead of silent `return []`.
4. **Log structured parse failures** with the full response for debugging.

**Effort:** Small (1 hour).

---

### CR-4: Add One Integration Test with Real LLM

**Why this is critical:** 411 tests with mocked LLMs prove the plumbing works. They do not prove the system works. One integration test that runs the real pipeline on a subset of synthetic data — extraction through generation — proves the product actually delivers value.

**What to do:**
1. Add a test marked `@pytest.mark.integration` (skipped without API key)
2. Feed 3-5 synthetic threads through the real extraction pipeline
3. Validate: atoms are produced, have correct types, pass confidence filter
4. Feed atoms through scoring for one persona
5. Validate: scored atoms are ranked, critical items flagged
6. Optionally: feed through generation and validate output structure

```python
@pytest.mark.integration
def test_end_to_end_pipeline():
    """Full pipeline with real LLM produces valid scored digest."""
    client = create_llm_client()  # Requires ANTHROPIC_API_KEY
    
    # Layer 1: Ingestion
    messages = load_message_stream()[:20]
    threads = group_by_thread(messages)
    windows = assemble_context_windows(threads[:5])
    
    # Layer 2: Extraction
    runner = ExtractionRunner(client)
    atoms = runner.extract(windows)
    assert len(atoms) > 0, "Extraction produced no atoms"
    
    # Layer 4: Scoring
    persona = get_persona("U001")
    scored = score_atoms(atoms, persona)
    assert len(scored) > 0, "Scoring produced no results"
    assert scored[0].score >= scored[-1].score, "Not sorted by score"
```

**Effort:** Small (30 minutes).

---

## 10. Next Steps (Future Work)

These are valuable improvements but are lower priority than the 4 critical recommendations above. They represent the path from "compelling demo" to "production system."

### Engineering

| # | Issue | Effort | Impact | Notes |
|---|-------|--------|--------|-------|
| NS-1 | **Async concurrency** for LLM calls (semaphore-bounded `asyncio.gather`) | Medium | High | 10-20x faster pipeline; needed before real deployment |
| NS-2 | **Move config from import-time to call-time** via FastAPI `Depends` | Medium | Medium | Testability, reloadability, no side effects |
| NS-3 | **Make `anthropic` an optional dependency** | Small | Medium | True provider agnosticism |
| NS-4 | **Add `pyyaml` to explicit dependencies** | Trivial | Low | Prevent breakage |
| NS-5 | **Token counting and cost tracking** per LLM call | Medium | Medium | Operational visibility |

### Scoring & Relevance

| # | Issue | Effort | Impact | Notes |
|---|-------|--------|--------|-------|
| NS-6 | **Calibrate scoring dimensions** — normalize distributions | Medium | High | Current discrete/continuous mix skews weights |
| NS-7 | **Phase distance scoring** instead of binary overlap | Small | Medium | DVT→PVT should score higher than Concept→MP |
| NS-8 | **Atom deduplication** — semantic similarity within (type, workstream) | Medium | Medium | Overlapping windows produce duplicates |
| NS-9 | **Enforce `ScoringWeights` sum-to-one** with model validator | Small | Medium | Prevent silent scoring bugs |
| NS-10 | **2-hop social signal** from collaborator graph | Medium | Low | Transitive social relevance |

### LLM Pipeline

| # | Issue | Effort | Impact | Notes |
|---|-------|--------|--------|-------|
| NS-11 | **Two-stage extraction** — coarse extract → enrich | Large | High | Better recall and precision |
| NS-12 | **Strip metadata from validation prompt** | Small | Low | Remove confidence bias |

### Frontend

| # | Issue | Effort | Impact | Notes |
|---|-------|--------|--------|-------|
| NS-13 | **Error boundaries + data fetching library** (`@tanstack/react-query`) | Medium | Medium | Production UX |
| NS-14 | **Fetch personas from API** instead of hardcoding | Small | Low | Single source of truth |
| NS-15 | **Accessibility audit** (ARIA, keyboard nav, contrast) | Medium | Low | Required before production |

### Architecture (v2+)

| # | Issue | Effort | Impact | Notes |
|---|-------|--------|--------|-------|
| NS-16 | **Persistent storage** (PostgreSQL/SQLite) for graph and atoms | Large | High | Production data layer |
| NS-17 | **Embedding-based RELATES_TO edges** in knowledge graph | Large | High | Semantic similarity for dedup + discovery |
| NS-18 | **Evaluate LangGraph** when dynamic routing or human-in-the-loop is needed | Large | Medium | Not yet — current architecture is simpler |
| NS-19 | **Real Slack integration** via Slack Events API | Large | High | Replace synthetic data |
| NS-20 | **Streaming digests** to frontend as sections complete | Medium | Medium | Better UX for long generation |

---

## 11. Conclusion

EverCurrent demonstrates genuine systems thinking. The domain model (atoms, personas, five-dimensional scoring) is the right abstraction. The phase-per-workstream insight is correct. The code quality is professional.

**The strategic insight this review adds:** Ye Wang described EverCurrent's knowledge graph as the most critical component, and the system's core value as change tracking over time. Your prototype is excellent at *computing* relevance in a single pass — but it doesn't *remember* anything. Adding a persistent knowledge graph with temporal edges transforms this from a batch ETL pipeline into something that demonstrates understanding of the actual product vision.

**The 4 critical recommendations in priority order:**

1. **Wire the pipeline end-to-end** — table stakes for a working demo
2. **Add a knowledge graph layer** — the highest-leverage alignment with EverCurrent's vision
3. **Add structured outputs + JSON recovery** — production ML engineering discipline
4. **Add one real integration test** — prove it works with real LLMs

Together, these create a narrative: *I built a system that extracts information from conversations, accumulates it as a knowledge graph, tracks how things change over time, and generates personalized briefings for different roles on the team. Here's a working demo.*

That's a compelling story for the follow-up meeting.

---

*Review generated by a simulated panel of principal engineers. All perspectives are unified in this document.*
