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
| Role-type alignment   | 0.20   | Role archetype x atom type matrix (4x8)          |
| Phase alignment       | 0.20   | Per-workstream phase x atom type matrix (5x8)    |
| Urgency               | 0.15   | Atom urgency: critical/high/medium/low           |
| Social signal         | 0.15   | Collaborator graph overlap, escalation language   |

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

Six gates enforced on every commit via `scripts/quality-gates.sh`:

| Gate                          | Tool              | Threshold       |
|-------------------------------|-------------------|-----------------|
| Linting                       | ruff check        | Zero violations  |
| Formatting                    | ruff format       | Zero violations  |
| Type checking                 | ty check          | Zero errors      |
| Tests + coverage              | pytest + pytest-cov | >= 90%        |
| Cyclomatic complexity         | radon cc          | <= 8 per function |
| Maintainability index         | radon mi          | A rating         |

Current stats: **348 tests, 99% coverage, all gates passing.**

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
│   ├── fixtures.py                # Fixture data store
│   ├── models/                    # Pydantic models
│   │   ├── atom.py                #   Atom, AtomSource, AtomWorkstreams
│   │   ├── digest.py              #   DigestSection
│   │   └── persona.py             #   Persona, DigestPreferences
│   ├── dataset/                   # Synthetic Slack dataset
│   │   ├── messages.py            #   150+ messages across 8 channels
│   │   └── schema.py              #   Message schema validation
│   ├── ingestion/                 # Layer 1: Message ingestion
│   │   ├── loader.py              #   Channel message loader
│   │   ├── threads.py             #   Thread grouping
│   │   ├── context_window.py      #   Context window builder
│   │   └── continuations.py       #   Continuation detection
│   ├── extraction/                # Layer 2: Atom extraction
│   │   ├── prompt.py              #   Extraction prompt design
│   │   ├── runner.py              #   LLM extraction runner
│   │   ├── filter.py              #   Duplicate/noise filtering
│   │   └── validation.py          #   Atom validation
│   ├── context/                   # Layer 3: Context backbone
│   │   ├── roster.py              #   Team roster
│   │   ├── workstreams.py         #   Workstream registry
│   │   ├── phases.py              #   Per-workstream phase vectors
│   │   └── personas.py            #   Three demo personas
│   ├── scoring/                   # Layer 4: Relevance scoring
│   │   ├── workstream_proximity.py
│   │   ├── role_alignment.py
│   │   ├── phase_alignment.py
│   │   ├── urgency.py
│   │   ├── social_signal.py
│   │   └── composite.py           #   Weighted composite + ranking
│   └── generation/                # Layer 5: Digest generation
│       ├── prompt.py              #   Briefing tone system prompt
│       ├── runner.py              #   DigestGenerator (Anthropic API)
│       └── assembler.py           #   DigestAssembler orchestrator
├── tests/                         # 348 tests, 99% coverage
│   ├── test_evaluation/           #   Eval criteria 1-3 (17 tests)
│   ├── test_scoring/              #   Scoring dimensions + composite
│   ├── test_generation/           #   Prompt, runner, assembler
│   ├── test_extraction/           #   Prompt, runner, filter, validation
│   ├── test_ingestion/            #   Loader, threads, context windows
│   ├── test_context/              #   Roster, workstreams, phases, personas
│   ├── test_dataset/              #   Messages, schema, buried signals
│   └── test_models/               #   Atom, digest, persona models
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
│   └── quality-gates.sh           #   Six quality gates
├── design-document.rst            #   Full technical design document
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

| Component   | Technology                                    |
|-------------|-----------------------------------------------|
| Backend     | Python 3.13, FastAPI, Pydantic v2, uvicorn    |
| LLM         | Anthropic Claude API                          |
| Frontend    | React 18, TypeScript, Tailwind CSS, Vite      |
| Testing     | pytest, pytest-cov, pytest-asyncio            |
| Linting     | ruff (lint + format), ty (type check)         |
| Metrics     | radon (cyclomatic complexity, maintainability) |
| Deps        | uv (package management)                       |
