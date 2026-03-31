# EverCurrent

Context-aware daily digest tool for robotics hardware teams.

EverCurrent solves the critical information loss problem in hardware engineering:
a missed Slack thread about a spec change can cost weeks, dollars, and physical
waste. The system ingests team communication, extracts structured atoms of
information, scores them against each engineer's context, and generates
personalized daily digests - so every team member sees exactly what matters to
them.

## Architecture

EverCurrent is a five-layer pipeline that transforms raw Slack messages into
persona-specific daily digests:

![EverCurrent Architecture](docs/_static/architecture.svg)

### Scoring Dimensions

| Dimension             | Weight | Signal                                          |
|-----------------------|--------|--------------------------------------------------|
| Workstream proximity  | 0.30   | Persona's affinity to atom's workstream(s)       |
| Role-type alignment   | 0.20   | Role archetype x atom type matrix (5x8)          |
| Phase alignment       | 0.20   | Graduated distance scoring across 5 phases       |
| Urgency               | 0.15   | Atom urgency: critical/high/medium/low           |
| Social signal         | 0.15   | Collaborator graph overlap, participant matching  |

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for frontend)

### Backend

```bash
# Install dependencies
uv sync

# Run quality gates
bash scripts/quality-gates.sh

# Start the API server
uv run uvicorn evercurrent.app:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 to see the digest UI.

## API Endpoints

| Method | Path                    | Description                              |
|--------|-------------------------|------------------------------------------|
| GET    | `/health`               | Application health status                |
| POST   | `/pipeline/run`         | Trigger extraction-to-digest pipeline    |
| GET    | `/digest/{persona_id}`  | Retrieve personalized digest             |

The digest endpoint accepts an optional `phase_override` query parameter
(format: `workstream:phase`) to demonstrate phase sensitivity.

```bash
# Fetch Maya Chen's digest
curl http://localhost:8000/digest/U001

# Fetch with phase override (thermal moved to DVT)
curl "http://localhost:8000/digest/U001?phase_override=thermal:DVT"
```

## Demo Personas

Three personas demonstrate differential relevance - the same data produces
meaningfully different digests for each:

| Persona         | ID   | Role                      | Top Workstreams                    |
|-----------------|------|---------------------------|------------------------------------|
| Maya Chen       | U001 | Senior Mechanical Engineer | chassis (1.0), thermal (0.85)     |
| Elena Vasquez   | U007 | Supply Chain Manager       | supply-chain (1.0), chassis (0.5) |
| Ryan Torres     | U010 | Engineering Manager        | chassis (0.8), drivetrain (0.8)   |

**What to look for:**

- **Maya** sees chassis spec changes and thermal risks prominently
- **Elena** sees supply-chain decisions and vendor lead-time risks, even when
  they originate in channels she doesn't follow
- **Ryan** sees cross-team blockers and decisions that affect multiple workstreams
- **Phase toggle**: switching thermal from EVT to DVT shifts atom rankings
  visibly (at least 2 items change position)

## Quality Gates

Eight gates enforced on every commit via `scripts/quality-gates.sh`:

| Gate                          | Tool              | Threshold           |
|-------------------------------|-------------------|---------------------|
| Linting                       | ruff check        | Zero violations     |
| Formatting                    | ruff format       | Zero violations     |
| Type checking                 | ty check          | Zero errors         |
| Tests + coverage              | pytest + pytest-cov | >= 90%            |
| Cyclomatic complexity         | radon cc          | <= 8 per function   |
| Maintainability index         | radon mi          | A rating            |
| Docstring coverage            | interrogate       | >= 95%              |
| Dead code detection           | vulture           | min-confidence 80   |

Current stats: **531 tests, 99% coverage, all gates passing.**

## Evaluation Criteria

Three success criteria from the design document (section 10.1):

### Criterion 1: Differential Relevance (7 tests)

Same atoms, meaningfully different digests. Maya ranks chassis/thermal highest,
Elena ranks supply-chain highest, Ryan ranks blockers and cross-team risks
highest. Top-ranked atoms differ across personas.

### Criterion 2: Buried Signal Surfacing (5 tests)

Three planted cross-workstream signals surface for the correct personas:
1. Magnesium housing decision (chassis) surfaces for Elena (supply-chain)
2. Thermal interface root cause surfaces for Maya
3. FPGA lead time risk (firmware) surfaces for Elena (supply-chain)

### Criterion 3: Phase Sensitivity (5 tests)

Toggling a workstream's phase produces visible scoring changes. EVT atoms score
higher in EVT phase, DVT atoms score higher in DVT phase, and at least 2 items
change rank position on phase toggle.

## Project Structure

```
evercurrent/
├── src/evercurrent/
│   ├── app.py                     # FastAPI application
│   ├── pipeline.py                # Orchestrator (sync + async)
│   ├── fixtures.py                # In-memory fixture data store
│   ├── models/                    # Pydantic models
│   │   ├── atom.py                #   Atom, AtomSource, AtomWorkstreams
│   │   ├── digest.py              #   DigestSection
│   │   ├── persona.py             #   Persona, DigestPreferences
│   │   └── responses.py           #   Coarse/Enrichment/Validation responses
│   ├── dataset/                   # Synthetic Slack dataset
│   │   ├── messages.py            #   Loads from data/slack_messages.json
│   │   └── schema.py              #   Message schema validation
│   ├── ingestion/                 # Layer 1: Message ingestion
│   │   ├── loader.py              #   Channel message loader
│   │   ├── threads.py             #   Thread grouping
│   │   ├── context_window.py      #   Context window builder
│   │   └── continuations.py       #   Continuation detection
│   ├── extraction/                # Layer 2: Two-stage atom extraction
│   │   ├── prompt.py              #   Coarse + enrichment prompts
│   │   ├── runner.py              #   Two-stage runner (sync + async)
│   │   ├── filter.py              #   Confidence filtering
│   │   └── validation.py          #   Two-pass validation
│   ├── context/                   # Layer 3: Context backbone
│   │   ├── roster.py              #   Team roster
│   │   ├── workstreams.py         #   Workstream registry
│   │   ├── phases.py              #   Per-workstream phase vectors
│   │   └── personas.py            #   Three demo personas
│   ├── scoring/                   # Layer 4: Relevance scoring
│   │   ├── workstream_proximity.py
│   │   ├── role_alignment.py      #   5x8 role-type matrix
│   │   ├── phase_alignment.py     #   Graduated distance scoring
│   │   ├── urgency.py             #   Uniform spacing (0.25 intervals)
│   │   ├── social_signal.py       #   4-level differentiated scoring
│   │   └── composite.py           #   Weighted composite + ranking
│   ├── generation/                # Layer 5: Digest generation
│   │   ├── prompt.py              #   Briefing tone system prompt
│   │   ├── runner.py              #   DigestGenerator (sync + async)
│   │   └── assembler.py           #   DigestAssembler orchestrator
│   ├── llm/                       # Model-agnostic LLM client harness
│   │   ├── types.py               #   LLMClient + AsyncLLMClient protocols
│   │   ├── anthropic.py           #   Anthropic Claude adapter
│   │   ├── openai.py              #   OpenAI adapter
│   │   ├── google.py              #   Google Gemini adapter
│   │   └── factory.py             #   Provider factory
│   ├── config/                    # YAML-based configuration
│   │   └── loader.py              #   Config loader with caching
│   └── graph/                     # Knowledge graph (placeholder)
│       └── client.py              #   Neo4j client
├── config/                        # YAML configuration files
│   ├── pipeline.yml               #   Model, tokens, CORS, thresholds
│   ├── scoring.yml                #   Weights, matrices, calibrated values
│   ├── personas.yml               #   Demo persona definitions
│   ├── phases.yml                 #   Per-workstream phase defaults
│   └── workstreams.yml            #   Channel/component mappings
├── data/
│   └── slack_messages.json        # Slack-API-shaped fixture (307 messages)
├── tests/                         # 531 tests, 99% coverage
│   ├── test_evaluation/           #   Eval criteria 1-3 (17 tests)
│   ├── test_scoring/              #   Scoring dimensions + calibration
│   ├── test_generation/           #   Prompt, runner, assembler
│   ├── test_extraction/           #   Two-stage, runner, filter, validation
│   ├── test_ingestion/            #   Loader, threads, context windows
│   ├── test_context/              #   Roster, workstreams, phases, personas
│   ├── test_dataset/              #   Fixture, schema, buried signals
│   ├── test_config/               #   YAML config loader
│   ├── test_llm/                  #   All LLM adapters + factory
│   ├── test_graph/                #   Neo4j client
│   └── test_models/               #   Atom, digest, persona, responses
├── frontend/
│   └── src/
│       ├── App.tsx                #   Main app with state management
│       ├── api/client.ts          #   API client
│       ├── components/
│       │   ├── PersonaSelector.tsx #   Tab-based persona switcher
│       │   ├── DigestDisplay.tsx   #   Four-section digest renderer
│       │   ├── PhaseToggle.tsx     #   Phase override demo panel
│       │   └── PipelineRunner.tsx  #   Pipeline trigger + progress
│       └── types/                 #   TypeScript interfaces
├── scripts/
│   └── quality-gates.sh           #   Eight quality gates
├── docs/                          #   Sphinx documentation
│   ├── design-document.rst        #   Full technical design document
│   ├── next-steps.rst             #   Follow-on work and scaling plan
│   └── api/                       #   Auto-generated API reference
├── vulture_whitelist.py           #   Dead code false positive whitelist
├── Makefile                       #   Build automation targets
└── pyproject.toml                 #   Project config (uv, ruff, pytest, radon)
```

## Design Decisions

- **Phase is per-workstream, not project-wide** (ADR-004): Chassis can be in DVT
  while thermal is still in late EVT. The scoring engine checks all persona
  workstream phases, not just the atom's originating workstream.
- **Relevance is relational, not intrinsic**: The same spec change atom is
  critical to the chassis engineer and irrelevant to the firmware developer.
  Scoring is always (atom, persona) pairs.
- **Briefing tone, not newsletter**: Digests read like a competent chief of
  staff's briefing - terse, specific, no editorializing. The moment the digest
  adds opinions, it loses engineering team trust.
- **Critical threshold overflow**: Atoms scoring above 0.85 always appear in the
  digest, even beyond the top-N limit, ensuring urgent items are never dropped.
- **Cross-workstream affected tags**: Atoms carry both originating and affected
  workstream lists, enabling buried signal surfacing across team boundaries.

## Tech Stack

| Component   | Technology                                          |
|-------------|-----------------------------------------------------|
| Backend     | Python 3.13, FastAPI, Pydantic v2, uvicorn          |
| LLM         | Model-agnostic (Anthropic, OpenAI, Google) via instructor |
| Frontend    | React 19, TypeScript, Tailwind CSS, Vite            |
| Testing     | pytest, pytest-cov, pytest-asyncio                  |
| Linting     | ruff (lint + format), ty (type check)               |
| Metrics     | radon (complexity), interrogate (docstrings), vulture (dead code) |
| Docs        | Sphinx, autodoc, napoleon, sphinx-autodoc-typehints |
| Deps        | uv (package management)                             |
