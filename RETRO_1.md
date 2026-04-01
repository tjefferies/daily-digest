# Retrospective #1 - EverCurrent Codebase Review

**Date:** 2026-04-01
**Reviewers:** Principal engineering panel (Slack, Google AI, Google Frontend, Stripe Product, Boston Dynamics Staff, Oxford CS/Math)
**Scope:** 98 commits, 52 Python source files (6,095 LOC), 8,528 LOC tests

---

## Executive Summary

The codebase has the bones of a strong extraction pipeline but has accumulated significant dead code and architectural complexity that prevents the prototype from functioning end-to-end. **The #1 priority is a working demo with 3 personas.** Everything else is secondary.

---

## What Worked

1. **Two-stage extraction (coarse → enrich)** - This was the right architectural call. Reducing cognitive load per LLM call improves extraction quality measurably. Keep this.

2. **Batch API adoption** - Moving from per-request calls to Anthropic Message Batches was necessary. 50% cost savings, no rate limiting. The tool_use approach for structured output eliminates the brittle markdown-fencing parsing.

3. **Neo4j graph model** - Atom → Channel/Workstream/Participant relationships are a natural fit for graph queries. The Cypher queries for blocker patterns and spec changes are elegant.

4. **FAISS vectorstore** - Persistent embedding cache prevents redundant computation. The CachedEmbedder wrapper is clean.

5. **Config-driven pipeline** - `pipeline.yml` for model, thresholds, concurrency. This pattern needs to extend to prompts and tool schemas.

6. **Hybrid continuation detection** - Structural fast-path (regex) + semantic fallback (embeddings) is the right layered approach.

## What Didn't Work

### 1. Multi-Provider Abstraction (Critical Mistake)

**Files:** `llm/openai.py` (210 LOC), `llm/google.py` (209 LOC), `llm/factory.py` (189 LOC), `llm/types.py` (61 LOC)

We built full OpenAI and Google adapters with instructor integration, async variants, and factory patterns - **none of which are used**. The app exclusively uses Anthropic. This is 669 LOC of dead code that added complexity to every LLM-touching module, forced an abstraction layer (`LLMClient` protocol) that leaks through the codebase, and blocked adoption of Anthropic-specific features (batch API, tool_use).

**Lesson:** Build for one provider first. Abstract when you have a second paying customer who needs it.

### 2. Instructor Dependency

**Impact:** Added to every LLM adapter, created coupling between structured output and the LLM client interface.

Instructor was adopted for structured output parsing, but Anthropic's native `tool_use` achieves the same thing without a dependency. The batch runner already proved this - tool_use returns clean JSON via tool calls. Instructor adds retry logic we don't need (the batch API handles retries internally) and blocks adoption of batch-native patterns.

**Lesson:** Don't add middleware when the underlying API already provides the capability.

### 3. Sync Code Paths

**Files:** `ExtractionRunner` (sync), `DigestGenerator` (sync), `run_pipeline` (sync), `validate_atoms` (sync), `DigestAssembler` (sync)

Every module was built with both sync and async variants. The sync paths are never called from the app - only from tests. This doubled the code surface area and created a maintenance burden where every feature had to be implemented twice.

**Lesson:** Pick async from day 1 for a pipeline that makes network calls. Don't maintain sync mirrors.

### 4. 90% Test Coverage as a Goal

574 tests, 90%+ coverage - impressive numbers that hide a critical gap: **no integration tests**. Every test mocks the LLM, mocks Neo4j, mocks FAISS. When the app runs against real services, it fails in ways the tests never caught:

- Neo4j `localhost` vs Docker hostname (`neo4j:7687`)
- Cypher syntax rejected by Neo4j 2025 (aggregation + ORDER BY)
- Batch API returning `canceled` results
- LLM returning markdown-fenced JSON instead of raw JSON
- `faiss-cpu` not installed in Docker image

Every one of these was a production bug discovered at runtime, not by the 574 passing tests.

**Lesson:** 80% coverage with 5 real integration tests is worth more than 95% coverage with 574 mocked tests.

### 5. No Persistent State Between Runs

The pipeline re-processes all 116 threads every time, making ~500 LLM calls. Neo4j dedup was added but the approach is fragile - it depends on the graph being populated, which itself depends on the pipeline completing successfully. The correct approach is Postgres-backed delta processing: persist bundles, check for changes, only extract new/modified bundles.

**Lesson:** Persistent state is not optional for a pipeline that costs money per run. Design for delta from the start.

### 6. Blocking Request Architecture

`POST /pipeline/run` originally blocked for 5-10 minutes until all 116 windows were processed. The nginx proxy timed out at 60s, killing the request. Even after making it async, the batch API polling blocks the async task - the status endpoint works but the pipeline can't be canceled.

**Lesson:** Long-running operations should always be fire-and-forget with polling. Design the API this way from the start.

---

## Dead Code Inventory

| File/Symbol | LOC | Status |
|---|---|---|
| `llm/openai.py` | 210 | Never used in production |
| `llm/google.py` | 209 | Never used in production |
| `ExtractionRunner` (sync) | 80 | Only used in sync pipeline (test-only) |
| `AsyncExtractionRunner` | 90 | Replaced by `BatchExtractionRunner` |
| `DigestGenerator` (sync) | 60 | Only async variant used |
| `run_pipeline` (sync) | 60 | Only async variant used |
| `validate_atoms` (sync) | 20 | Only async variant used |
| `ExtractionResponse` (legacy) | 8 | Replaced by Coarse+Enrichment |
| `build_extraction_prompt` (legacy) | 80 | Replaced by coarse+enrichment prompts |
| **Total dead code** | **~817** | **13% of source LOC** |

---

## V2 Architecture (Target)

```
                    ┌─────────────┐
                    │  Frontend   │ React + polling
                    │  :5173      │ progress UI
                    └──────┬──────┘
                           │ /api/
                    ┌──────┴──────┐
                    │   FastAPI   │ async-only
                    │   :8000     │ batch pipeline
                    └──┬───┬───┬──┘
                       │   │   │
              ┌────────┘   │   └────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Postgres │ │  Neo4j   │ │  FAISS   │
        │ bundles  │ │  atoms   │ │ vectors  │
        │ atoms    │ │  graph   │ │ cache    │
        │ batches  │ │  queries │ │          │
        └──────────┘ └──────────┘ └──────────┘
              ▲
              │ delta check
        ┌─────┴──────┐
        │  Anthropic  │
        │  Batch API  │ tool_use structured output
        │  (50% off)  │
        └─────────────┘
```

**Key principles:**
- Anthropic-only, batch API, tool_use for structured output
- Postgres is the system of record (bundles, atoms, batch logs)
- Neo4j for graph queries (persona relevance, workstream relationships)
- FAISS for embedding cache (continuation detection)
- Async-only, no sync code paths
- Delta processing, no kill-and-fill
- All config in YAML (prompts, constants, tool schemas)
- 80% coverage + integration tests > 90% coverage + mocks

---

## Dependency Graph

```
evercurrent-tdf (EPIC)
└── evercurrent-ya1 (Prune dead code) ← START HERE
    ├── evercurrent-v1z (Postgres + SQLAlchemy)
    │   ├── evercurrent-kwn (Delta pipeline)
    │   │   ├── evercurrent-a04 (Frontend rewrite)
    │   │   │   └── evercurrent-6n9 (Frontend Neo4j startup)
    │   │   ├── evercurrent-zbv (Design doc update)
    │   │   └── evercurrent-dx3 (Integration tests)
    │   └── evercurrent-dmi (Batch logging)
    ├── evercurrent-gjx (Remove instructor → tool_use)
    ├── evercurrent-017 (Prompts to YAML)
    ├── evercurrent-dhe (FAISS IndexFlatIP)
    └── evercurrent-do1 (Rate limit safeguards)
```

---

## Recommendation

Start with `evercurrent-ya1` (prune dead code). It's the gate for everything else and immediately reduces the codebase by ~800 LOC. Then `evercurrent-v1z` (Postgres) and `evercurrent-kwn` (delta pipeline) are the critical path to a working prototype that doesn't waste money on duplicate LLM calls.

**The NUMBER ONE goal is a working prototype with the three personas.**
