# EverCurrent

Context-aware daily digest tool for robotics hardware teams.

EverCurrent solves the critical information loss problem in hardware engineering:
a missed Slack thread about a spec change can cost weeks, dollars, and physical
waste. The system ingests team communication, extracts structured atoms of
information, scores them against each engineer's context, and generates
personalized daily digests - so every team member sees exactly what matters to
them.

## Architecture

EverCurrent is an async pipeline that transforms raw Slack messages into
persona-specific daily digests via the Anthropic Message Batches API:

![EverCurrent Architecture](docs/_static/architecture.svg)

**Key principles:**
- **Anthropic-only** with Message Batches API (50% cost savings)
- **tool_use** for structured output - no instructor dependency
- **Async-only** - no sync code paths
- **Delta processing** - Postgres stores bundles; only new bundles are extracted
- **Config-driven** - all prompts in `config/prompts.yml`, all constants in `config/pipeline.yml`

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker + Docker Compose (for Neo4j, Postgres)
- Node.js 22+ (for frontend)

### Docker Compose (recommended)

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Start everything: backend, frontend, Neo4j, Postgres
make serve-all

# Or manually:
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Neo4j Browser: http://localhost:7474
- Postgres: localhost:5433

### Local Development

```bash
# Install all dependencies
uv sync --all-groups

# Copy .env.sample to .env and set ANTHROPIC_API_KEY
cp .env.sample .env

# Run quality gates
bash scripts/quality-gates.sh

# Start the API server
PYTHONPATH=src uv run uvicorn evercurrent.app:app --reload --port 8000

# Start the frontend
cd frontend && npm run dev
```

## API Endpoints

| Method | Path                    | Description                                    |
|--------|-------------------------|------------------------------------------------|
| GET    | `/health`               | Application health status                      |
| POST   | `/pipeline/run`         | Start extraction pipeline (returns immediately) |
| GET    | `/pipeline/status`      | Poll pipeline progress (batch counts)          |
| GET    | `/digest/{persona_id}`  | Retrieve personalized digest (cached)          |

The pipeline runs asynchronously. Poll `/pipeline/status` for real-time
batch progress:

```bash
# Start the pipeline
curl -X POST http://localhost:8000/pipeline/run

# Poll for progress
curl http://localhost:8000/pipeline/status
# {"state":"running","stage":"extraction_stage1","batch_id":"msgbatch_...","progress":{"total":10,"succeeded":6,"processing":4,"errored":0}}

# Fetch Maya Chen's digest (instant from cache after pipeline completes)
curl http://localhost:8000/digest/U001
```

## Demo Personas

Three personas demonstrate differential relevance - the same data produces
meaningfully different digests for each:

| Persona         | ID   | Role                      | Top Workstreams                    |
|-----------------|------|---------------------------|------------------------------------|
| Maya Chen       | U001 | Senior Mechanical Engineer | chassis (1.0), thermal (0.85)     |
| Elena Vasquez   | U007 | Supply Chain Manager       | supply-chain (1.0), chassis (0.5) |
| Ryan Torres     | U010 | Engineering Manager        | chassis (0.8), drivetrain (0.8)   |

Persona switching in the frontend is **instant** - all 3 digests are preloaded
on startup from Neo4j cache.

## Quality Gates

Seven gates enforced via `scripts/quality-gates.sh`:

| Gate                          | Tool              | Threshold           |
|-------------------------------|-------------------|---------------------|
| Linting                       | ruff check        | Zero violations     |
| Formatting                    | ruff format       | Zero violations     |
| Tests + coverage              | pytest + pytest-cov | >= 80%            |
| Cyclomatic complexity         | radon cc          | <= 8 per function   |
| Maintainability index         | radon mi          | A rating            |
| Docstring coverage            | interrogate       | >= 95%              |
| Dead code detection           | vulture           | min-confidence 80   |

Current stats: **511 tests (490 unit + 21 integration), all gates passing.**

## Project Structure

```
evercurrent/
├── src/evercurrent/
│   ├── app.py                     # FastAPI app (async, precook digests)
│   ├── pipeline.py                # Pipeline orchestrator (async-only)
│   ├── models/                    # Pydantic models
│   │   ├── atom.py                #   Atom, AtomSource, AtomWorkstreams
│   │   ├── digest.py              #   DigestSection
│   │   ├── persona.py             #   Persona, DigestPreferences
│   │   └── responses.py           #   Coarse/Enrichment/Validation responses
│   ├── dataset/                   # Synthetic Slack dataset
│   │   ├── messages.py            #   Loads from data/slack_messages.json
│   │   └── schema.py              #   Message schema, team roster
│   ├── db/                        # Postgres persistence (async SQLAlchemy)
│   │   ├── models.py              #   Message, ThreadBundle, BundleMembership, Atom, BatchLog
│   │   ├── repository.py          #   persist_bundle, persist_atoms, get_processed_bundle_ts
│   │   ├── session.py             #   Async session factory
│   │   └── llm_logger.py          #   LLM request/response body logging
│   ├── ingestion/                 # Layer 1: Message ingestion
│   │   ├── threads.py             #   Thread grouping (Pass 1)
│   │   ├── continuations.py       #   Semantic + structural continuation detection (Pass 2)
│   │   ├── embeddings.py          #   Embedder protocol, FAISS cosine similarity
│   │   ├── vectorstore.py         #   FAISS IndexFlatIP persistent cache
│   │   ├── cached_embedder.py     #   CachedEmbedder (FAISS dedup)
│   │   └── context_window.py      #   Context window assembly + compression
│   ├── extraction/                # Layer 2: Two-stage atom extraction
│   │   ├── batch_runner.py        #   Anthropic Batch API with tool_use
│   │   ├── runner.py              #   AsyncExtractionRunner (per-request fallback)
│   │   ├── prompt.py              #   Loads from config/prompts.yml
│   │   ├── filter.py              #   Confidence filtering
│   │   └── validation.py          #   Rate-limited async validation
│   ├── context/                   # Layer 3: Context backbone
│   │   ├── personas.py            #   Three demo personas
│   │   ├── workstreams.py         #   Workstream registry
│   │   └── phases.py              #   Per-workstream phase vectors
│   ├── scoring/                   # Layer 4: Relevance scoring
│   │   ├── composite.py           #   Weighted 5-dimension composite
│   │   ├── workstream_proximity.py
│   │   ├── role_alignment.py      #   5x8 role-type matrix
│   │   ├── phase_alignment.py     #   Graduated distance scoring
│   │   ├── urgency.py             #   Uniform spacing
│   │   └── social_signal.py       #   Collaborator graph scoring
│   ├── generation/                # Layer 5: Digest generation
│   │   ├── prompt.py              #   Loads from config/prompts.yml
│   │   ├── runner.py              #   AsyncDigestGenerator
│   │   └── assembler.py           #   AsyncDigestAssembler orchestrator
│   ├── llm/                       # Anthropic LLM client (async-only)
│   │   ├── types.py               #   AsyncLLMClient protocol
│   │   ├── anthropic.py           #   AsyncAnthropicAdapter (tool_use)
│   │   └── factory.py             #   create_async_llm_client()
│   ├── config/                    # Config loader
│   │   └── loader.py              #   YAML loader + .env + env overrides
│   └── graph/                     # Neo4j knowledge graph
│       └── client.py              #   GraphClient (async, atom persistence)
├── config/                        # YAML configuration
│   ├── pipeline.yml               #   Model, tokens, thresholds, concurrency
│   ├── prompts.yml                #   All LLM prompts (editable without code)
│   ├── scoring.yml                #   Scoring weights and matrices
│   ├── personas.yml               #   Demo persona definitions
│   ├── phases.yml                 #   Per-workstream phase defaults
│   └── workstreams.yml            #   Channel/component mappings
├── data/
│   └── slack_messages.json        # Slack-API-shaped fixture (307 messages)
├── docker-compose.yml             # Backend + Frontend + Neo4j + Postgres
├── backend.Dockerfile             # Multi-stage Python build
├── frontend/                      # React frontend
│   ├── src/
│   │   ├── App.tsx                #   Preloads digests, instant persona switch
│   │   ├── api/client.ts          #   API client with PipelineStatus polling
│   │   └── components/
│   │       ├── PipelineRunner.tsx  #   Real batch progress bar
│   │       ├── PersonaSelector.tsx #   3 demo personas
│   │       ├── DigestDisplay.tsx   #   Four-section digest renderer
│   │       └── PhaseToggle.tsx     #   Phase override demo panel
│   ├── Dockerfile                 #   Multi-stage nginx build
│   └── nginx.conf                 #   Reverse proxy + 600s timeout
├── alembic/                       # Postgres migrations (async)
├── scripts/
│   ├── quality-gates.sh           #   7 quality gates
│   ├── smoke-test.sh              #   E2E 3-window smoke test
│   └── smoke_test_runner.py       #   Smoke test Python runner
├── tests/                         # 511 tests
│   ├── test_integration/          #   FAISS + Postgres roundtrip tests
│   ├── test_db/                   #   SQLAlchemy model + repository tests
│   ├── test_extraction/           #   Batch runner, rate limits, validation
│   ├── test_ingestion/            #   Threads, continuations, embeddings, vectorstore
│   ├── test_scoring/              #   5 scoring dimensions + calibration
│   ├── test_generation/           #   Async digest generation
│   └── ...                        #   Config, endpoints, graph, models, etc.
├── RETRO_1.md                     # V2 retrospective (lessons learned)
└── pyproject.toml                 # Project config (uv, ruff, pytest, radon)
```

## Tech Stack

| Component     | Technology                                            |
|---------------|-------------------------------------------------------|
| Backend       | Python 3.13, FastAPI, Pydantic v2, uvicorn           |
| LLM           | Anthropic Claude (Batch API + tool_use)              |
| Database      | Postgres 16 (SQLAlchemy async), Neo4j, FAISS         |
| Frontend      | React, TypeScript, Tailwind CSS, Vite                |
| Orchestration | Docker Compose                                        |
| Testing       | pytest, pytest-cov, pytest-asyncio, aiosqlite        |
| Linting       | ruff (lint + format)                                  |
| Metrics       | radon (complexity), interrogate (docstrings), vulture |
| Docs          | Sphinx + furo theme                                   |
| Deps          | uv (package management), python-dotenv               |
