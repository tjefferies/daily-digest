#!/usr/bin/env bash
# issues.sh - Create the full beads epic hierarchy for EverCurrent Daily Digest Tool
#
# Architecture (design-document.rst, 5-layer pipeline):
#   E0 Python Tooling & Quality Infra ← must come first (pyproject.toml, ruff, pytest, ty, radon)
#   E1 Foundation & Infrastructure    ← depends on E0
#   E2 Synthetic Dataset              ← data drives all demo value
#   E3 Layer 1 - Ingestion            ← needs E2
#   E4 Layer 2 - Extraction Pipeline  ← needs E3
#   E5 Layer 3 - Context Backbone     ← needs E1, parallel to E4
#   E6 Layer 4 - Relevance Scoring    ← needs E4 + E5
#   E7 Layer 5 - Digest Generation    ← needs E6
#   E8 Frontend UI                    ← needs E7
#   E9 Evaluation & Demo Validation   ← needs E8 + E4
#
# Usage: bash issues.sh

set -euo pipefail

# ─── NUKE EXISTING ISSUES ────────────────────────────────────────────────────
echo "==> Deleting all existing issues..."
EXISTING=$(bd list --all --json 2>/dev/null | jq -r '.[].id' | tr '\n' ' ')
if [ -n "${EXISTING// }" ]; then
  # shellcheck disable=SC2086
  bd delete $EXISTING --cascade --force
  echo "    Deleted existing issues."
else
  echo "    No existing issues to delete."
fi

# ─── EPIC 0: Python Tooling & Quality Infrastructure ─────────────────────────
echo ""
echo "==> Creating Epic 0: Python Tooling & Quality Infrastructure"

EPIC_TOOL=$(bd create \
  --title="Python Tooling & Quality Infrastructure" \
  --type=epic \
  --priority=0 \
  --description="Set up the Python development toolchain that enforces code quality gates before any production code is written. Configures pyproject.toml with uv for dependency management, ruff for linting and formatting (Google docstrings, mccabe complexity cap at 8), pytest with coverage floor at 90%, ty for static type checking, and radon for maintainability auditing. Every subsequent epic inherits these quality constraints. This must be the very first thing built - the loop-dev.txt CI/CD process depends on all these tools being configured and passing before any issue can be closed." \
  --silent)

TOOL_1=$(bd create \
  --title="Configure pyproject.toml: production deps, dev group, src layout, uv lock" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Restructure pyproject.toml for a proper src-layout Python project managed by uv. Add [build-system] with hatchling. Add [project] dependencies: fastapi, uvicorn[standard], anthropic, pydantic>=2.0, httpx. Add [dependency-groups] dev: pytest>=8.0, pytest-cov>=6.0, pytest-asyncio>=0.24, ruff>=0.11, radon>=6.0, ty. Add [tool.setuptools.packages.find] with where=['src']. Run 'uv sync' to generate uv.lock and install all deps. Verify 'uv run python -c \"import fastapi\"' succeeds." \
  --silent)

TOOL_2=$(bd create \
  --title="Configure ruff: lint rules, Google docstrings, mccabe complexity cap" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Add ruff configuration to pyproject.toml. [tool.ruff]: target-version='py313', line-length=99. [tool.ruff.lint]: select E,F,W,I,N,D,UP,ANN,S,B,A,C4,C90,RET,SIM,TCH,ARG,PTH,ERA. [tool.ruff.lint.pydocstyle]: convention='google'. [tool.ruff.lint.mccabe]: max-complexity=8. [tool.ruff.lint.per-file-ignores]: 'tests/**'=['S101','ANN201','D103'] (allow assert, relaxed return annotations, and missing docstrings in tests). Verify 'uv run ruff check src/ tests/' passes on the empty project." \
  --silent)

TOOL_3=$(bd create \
  --title="Configure pytest: coverage floor 90%, asyncio mode, test discovery" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Add pytest configuration to pyproject.toml. [tool.pytest.ini_options]: asyncio_mode='auto', testpaths=['tests'], addopts='--cov=src --cov-report=term-missing --cov-fail-under=90 -v --strict-markers'. Register custom markers if needed. Verify 'uv run pytest' runs and exits 0 with 'no tests ran' (not an error, just no tests yet - coverage check is skipped when no tests exist)." \
  --silent)

TOOL_4=$(bd create \
  --title="Initialize src/evercurrent/ package layout and tests/ scaffold" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Create the directory structure that all subsequent epics write into: src/evercurrent/__init__.py (with __version__ and module docstring), src/evercurrent/py.typed (PEP 561 marker for type checker consumers), tests/__init__.py, tests/conftest.py (empty but present for pytest discovery). Verify: 'uv run python -c \"import evercurrent\"' succeeds, 'uv run pytest --collect-only' exits 0, 'uv run ruff check src/ tests/' exits 0." \
  --silent)

TOOL_5=$(bd create \
  --title="Configure ty for static type checking and verify radon CLI" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Set up ty (astral-sh type checker) configuration. Add [tool.ty] section to pyproject.toml if supported, or verify ty works with defaults against the src/ layout. Verify: 'uv run ty check src/' exits 0 on the empty package. Also verify radon CLI works: 'uv run radon cc src/ -a -nc' and 'uv run radon mi src/ -nc' both exit 0. These two tools are the cyclomatic complexity and maintainability index auditors referenced in the quality gates. No configuration files needed - they run from CLI flags." \
  --silent)

TOOL_6=$(bd create \
  --title="Add quality gate runner script and verify full toolchain end-to-end" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_TOOL" \
  --description="Create a scripts/quality-gates.sh that runs the full CI/CD gate sequence in order: (1) uv run ruff check src/ tests/, (2) uv run ruff format --check src/ tests/, (3) uv run ty check src/, (4) uv run pytest --tb=short, (5) uv run radon cc src/ -a -nc, (6) uv run radon mi src/ -nc. Script exits non-zero on first failure. Run it end-to-end on the empty project and verify all 6 gates pass. This script is what every issue closure must pass before bd close." \
  --silent)

# TOOL internal ordering: pyproject.toml first, then ruff/pytest/ty configs can be added to it,
# then package layout, then the e2e gate runner validates everything works together
bd dep add "$TOOL_2" "$TOOL_1"
bd dep add "$TOOL_3" "$TOOL_1"
bd dep add "$TOOL_4" "$TOOL_1"
bd dep add "$TOOL_5" "$TOOL_1"
bd dep add "$TOOL_6" "$TOOL_2"
bd dep add "$TOOL_6" "$TOOL_3"
bd dep add "$TOOL_6" "$TOOL_4"
bd dep add "$TOOL_6" "$TOOL_5"

echo "    EPIC_TOOL=$EPIC_TOOL  TOOL_1=$TOOL_1  TOOL_2=$TOOL_2  TOOL_3=$TOOL_3  TOOL_4=$TOOL_4  TOOL_5=$TOOL_5  TOOL_6=$TOOL_6"

# ─── EPIC 1: Foundation & Infrastructure ─────────────────────────────────────
echo ""
echo "==> Creating Epic 1: Foundation & Infrastructure"

EPIC_INFRA=$(bd create \
  --title="Foundation & Infrastructure" \
  --type=epic \
  --priority=0 \
  --description="Bootstrap the full-stack skeleton that every other epic depends on: FastAPI + Pydantic + Anthropic SDK backend, React + TypeScript + Tailwind frontend, in-memory fixture loader, and CORS/proxy wiring. Nothing else can start until these are in place. Tech stack per section 9.3 of design doc." \
  --silent)

INFRA_1=$(bd create \
  --title="Initialize FastAPI backend with Pydantic models and Anthropic SDK" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_INFRA" \
  --description="Scaffold the Python project: FastAPI app, uvicorn, anthropic SDK, pydantic v2. Define the top-level Atom Pydantic model with all 8 type literals (DECISION, SPEC_CHANGE, ACTION_ITEM, BLOCKER, RISK, TEST_RESULT, STATUS_UPDATE, QUESTION). Define the Persona and DigestSection models. Configure CORS for local frontend dev." \
  --silent)

INFRA_2=$(bd create \
  --title="Initialize React + TypeScript + Tailwind CSS frontend" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_INFRA" \
  --description="Bootstrap Vite + React + TypeScript project with Tailwind CSS. Configure vite.config.ts proxy to FastAPI on :8000. Set up folder structure: components/, pages/, types/, api/. Generate TypeScript types mirroring backend Pydantic models (Atom, Persona, DigestSection). No UI components yet - just the skeleton." \
  --silent)

INFRA_3=$(bd create \
  --title="Implement in-memory fixture store and startup data loader" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_INFRA" \
  --description="Implement a Python module that loads synthetic JSON fixture files from a /fixtures directory at FastAPI startup into an in-memory dict. Expose typed accessor functions: get_messages(), get_team_roster(), get_personas(), get_workstream_phases(). This is the single data source used by all pipeline layers. No DB needed for prototype (section 9.2)." \
  --silent)

INFRA_4=$(bd create \
  --title="Wire FastAPI pipeline endpoint skeleton with health check" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_INFRA" \
  --description="Add stub endpoints: GET /health, POST /pipeline/run, GET /digest/{persona_id}, GET /digest/{persona_id}?phase_override={ws}:{phase}. Return empty 200s initially so frontend development can begin before real layers are wired in. Enables parallel frontend and backend work." \
  --silent)

# INFRA internal ordering: loader needs backend models; endpoint skeleton needs the loader
bd dep add "$INFRA_3" "$INFRA_1"
bd dep add "$INFRA_4" "$INFRA_3"

echo "    EPIC_INFRA=$EPIC_INFRA  INFRA_1=$INFRA_1  INFRA_2=$INFRA_2  INFRA_3=$INFRA_3  INFRA_4=$INFRA_4"

# ─── EPIC 2: Synthetic Dataset ────────────────────────────────────────────────
echo ""
echo "==> Creating Epic 2: Synthetic Dataset"

EPIC_DATA=$(bd create \
  --title="Synthetic Dataset" \
  --type=epic \
  --priority=0 \
  --description="Design and hand-craft the two-day synthetic Slack dataset for an AMR robotics team across 8 channels, 20-30 team members, 300-500 messages. This is the core demo artifact - if the data feels fake, the entire demo falls apart. Must exhibit: (1) engineer-register prose, (2) three deliberately buried cross-workstream signals from section 9.4, (3) per-workstream phase diversity per section 6.3, (4) thread depth variety from 2-msg to 50-msg narrative arcs." \
  --silent)

DATA_1=$(bd create \
  --title="Define Slack message JSON schema and 8-channel + 20-person team roster" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_DATA" \
  --description="Specify the raw message JSON schema: {message_ts, thread_ts, channel, user_id, text, reactions: [{name, users}]}. Define 8 channels: #chassis-design, #drivetrain, #thermal-management, #power-systems, #sensors, #firmware, #supply-chain, #amr-general. Define 20-person team roster with user_id, name, title, and primary channels. This schema is the contract between the dataset and the ingestion layer." \
  --silent)

DATA_2=$(bd create \
  --title="Generate realistic AMR team conversations in engineer-register prose" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_DATA" \
  --description="Write 300-500 synthetic messages that read like engineers talking - not LLM filler. Engineer-register means: terse and technical ('pull-out force on snap fit measured at 12N, spec is 15N min'), cross-referential ('re: James thermal concern from yesterday'), jargon-dense (EVT, DVT, STEP files, Parasolid, torque spec, thermal interface material). Include both shallow 2-3 msg exchanges and deep 30-50 msg threads with a full narrative arc (problem to investigation to root cause to resolution)." \
  --silent)

DATA_3=$(bd create \
  --title="Plant the three buried cross-workstream signals" \
  --type=task \
  --priority=0 \
  --parent="$EPIC_DATA" \
  --description="Deliberately embed the three key buried signals from section 9.4: (1) In #chassis-design, a weight-reduction thread where someone casually says 'let's just go with magnesium for the housing' - implicit DECISION with procurement and certification impact; (2) In #testing, a motor overheating failure whose root cause implicates chassis/thermal thermal interface material - originating workstream is testing but affected workstreams are chassis and thermal; (3) In #supply-chain, an FPGA lead time update to 16 weeks that blocks a drivetrain milestone. Each signal must be buried in message 5+ of a thread, not in the opener." \
  --silent)

DATA_4=$(bd create \
  --title="Encode per-workstream phase diversity across the dataset" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_DATA" \
  --description="Configure messages to reflect the phase vector from section 6.3: Chassis=DVT, Drivetrain=DVT, Thermal=Late EVT, Power Systems=DVT, Sensors=EVT, Firmware=EVT, End-Effector=Concept. DVT conversations reference vendor readiness, tooling status, and validation test outcomes. EVT conversations reference design decisions and early test results. This phase diversity is what makes the phase-sensitivity demo work (Evaluation Criterion 3)." \
  --silent)

# DATA internal ordering: schema is written first; conversations and phases both build on schema
bd dep add "$DATA_2" "$DATA_1"
bd dep add "$DATA_3" "$DATA_2"
bd dep add "$DATA_4" "$DATA_2"

echo "    EPIC_DATA=$EPIC_DATA  DATA_1=$DATA_1  DATA_2=$DATA_2  DATA_3=$DATA_3  DATA_4=$DATA_4"

# ─── EPIC 3: Layer 1 - Ingestion ──────────────────────────────────────────────
echo ""
echo "==> Creating Epic 3: Layer 1 - Ingestion"

EPIC_L1=$(bd create \
  --title="Layer 1: Ingestion" \
  --type=epic \
  --priority=1 \
  --description="Implement the ingestion layer that transforms raw synthetic messages into ContextWindow objects ready for LLM extraction. The core algorithm is the 3-pass thread reconstruction described in section 4.1: (1) structural grouping by thread_ts, (2) implicit continuation detection via @-mentions and quote blocks, (3) context window assembly with compression for long threads. The compressed form preserves narrative arc while fitting LLM context limits." \
  --silent)

L1_1=$(bd create \
  --title="Implement message loader: parse fixture JSON into typed SlackMessage stream" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L1" \
  --description="Write an ingestion loader that reads from the in-memory fixture store and emits a flat, time-ordered stream of typed SlackMessage objects (message_ts, thread_ts, channel, user_id, text, reactions). This is the ingestion boundary - all downstream layers work with SlackMessage, not raw JSON dicts." \
  --silent)

L1_2=$(bd create \
  --title="Thread reconstruction Pass 1: structural grouping by thread_ts" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L1" \
  --description="Group all SlackMessage objects by thread_ts into ThreadBundle objects. A root message (thread_ts == message_ts) plus all its replies forms one ThreadBundle. Output: List[ThreadBundle] with root_message and replies fields. This handles all explicitly threaded Slack conversations." \
  --silent)

L1_3=$(bd create \
  --title="Thread reconstruction Pass 2: detect implicit continuations via @-mentions and quote blocks" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L1" \
  --description="Identify top-level messages that continue earlier threads without using Slack reply mechanism. Signals: (a) @-mention of the author of a recent thread's last message, (b) quote-block that matches earlier message text, (c) explicit back-reference ('re: the thermal issue'). Link these to their antecedent ThreadBundle as continuation_messages. Addresses assumption A3 in the design doc (threads used inconsistently)." \
  --silent)

L1_4=$(bd create \
  --title="Thread reconstruction Pass 3: context window assembly with long-thread compression" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L1" \
  --description="For each ThreadBundle assemble the final ContextWindow passed to Layer 2. If the thread fits within the token limit: include full thread. If over limit: compress to (root message + most-reacted messages + final 5 messages). This preserves narrative arc (opening problem + key reactions + resolution). ContextWindow output includes thread_text, channel, thread_ts, message_range for source anchoring per section 4.4." \
  --silent)

# L1 internal ordering: all 3 passes are strictly sequential
bd dep add "$L1_2" "$L1_1"
bd dep add "$L1_3" "$L1_2"
bd dep add "$L1_4" "$L1_3"

echo "    EPIC_L1=$EPIC_L1  L1_1=$L1_1  L1_2=$L1_2  L1_3=$L1_3  L1_4=$L1_4"

# ─── EPIC 4: Layer 2 - Extraction Pipeline ────────────────────────────────────
echo ""
echo "==> Creating Epic 4: Layer 2 - Extraction Pipeline"

EPIC_L2=$(bd create \
  --title="Layer 2: Extraction Pipeline" \
  --type=epic \
  --priority=1 \
  --description="Build the LLM extraction pipeline that converts ContextWindow objects into structured Atom objects (section 4.2-4.3). Key ADRs baked in: ADR-002 LLM over rule-based NLP because 'let's just go with magnesium' can't be caught with regex; ADR-003 one atom per discrete information unit not per thread; ADR-005 two-pass validation for SPEC_CHANGE and DECISION because a hallucinated torque value causes physical hardware damage." \
  --silent)

L2_1=$(bd create \
  --title="Finalize Atom Pydantic schema with all fields from section 4.3" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L2" \
  --description="Extend the Atom model stub from INFRA_1 with all extraction output fields: atom_id (uuid), type (8-literal enum), summary, detail, source {channel, thread_ts, message_range: [int,int], key_participants: [str]}, workstreams {originating: str, affected: [str]}, urgency (high|medium|low), confidence (float 0-1), implicit_decision (bool), phase_relevance (subset of Concept|EVT|DVT|PVT|MP). This schema is the contract between extraction and all downstream layers." \
  --silent)

L2_2=$(bd create \
  --title="Design LLM extraction prompt: conclusions, implicit decisions, cross-workstream tagging" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L2" \
  --description="Write the extraction system prompt per section 4.3. Three critical instructions: (1) Extract conclusions not discussions - a 30-msg debate produces one DECISION atom, not a debate summary; (2) Flag implicit decisions - 'let's just go with magnesium' is an implicit DECISION with confidence < 1.0; (3) Tag affected workstreams beyond just originating - a material change in #chassis-design also affects supply-chain, tooling, certification. Include the full Atom JSON schema in the prompt so output is structured JSON." \
  --silent)

L2_3=$(bd create \
  --title="Implement extraction runner: batch ContextWindows through Anthropic API" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L2" \
  --description="Build the ExtractionRunner class: iterate over all ContextWindows from Layer 1, call anthropic.messages.create() with extraction system prompt + context window text, parse JSON response into List[Atom]. Handle: API rate limiting with exponential backoff, JSON parse failures (retry or skip), batching for cost efficiency. Log extraction stats: units processed, atoms produced, confidence distribution." \
  --silent)

L2_4=$(bd create \
  --title="Implement two-pass validation for SPEC_CHANGE and DECISION atoms (ADR-005)" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L2" \
  --description="For all atoms where type is SPEC_CHANGE or DECISION: run a second Anthropic API call with (original ContextWindow text + extracted Atom JSON) and ask: 'Does this atom accurately represent what was said? Is anything overstated, understated, or fabricated?' Demote invalid atoms (confidence *= 0.5, add validation_warning field). Doubles cost for ~30% of atoms but justified - a hallucinated spec value in hardware means 500 wrong injection-molded parts (section 4.4)." \
  --silent)

L2_5=$(bd create \
  --title="Implement confidence threshold filter (default 0.7)" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L2" \
  --description="After extraction and validation, filter the atom list: atoms with confidence >= threshold pass through to scoring; atoms below threshold are excluded or placed in a low-confidence bucket. Threshold must be configurable (default 0.7 per section 4.4). Log how many atoms are filtered per threshold level so the evaluator can tune it." \
  --silent)

# L2 internal ordering: schema → prompt → runner; validation and filter are both post-runner
bd dep add "$L2_2" "$L2_1"
bd dep add "$L2_3" "$L2_2"
bd dep add "$L2_4" "$L2_3"
bd dep add "$L2_5" "$L2_3"

echo "    EPIC_L2=$EPIC_L2  L2_1=$L2_1  L2_2=$L2_2  L2_3=$L2_3  L2_4=$L2_4  L2_5=$L2_5"

# ─── EPIC 5: Layer 3 - Context Backbone ──────────────────────────────────────
echo ""
echo "==> Creating Epic 5: Layer 3 - Context Backbone"

EPIC_L3=$(bd create \
  --title="Layer 3: Context Backbone" \
  --type=epic \
  --priority=1 \
  --description="Build the world model that the relevance scoring layer queries: team roster with role archetypes, workstream registry with channel mappings, per-workstream phase vector (ADR-004: phase is a vector not a scalar), and three fully-specified demo personas (section 6.1). For prototype, manually populated from fixtures. In production, drawn from Slack metadata, org data, and self-declaration per section 6.2." \
  --silent)

L3_1=$(bd create \
  --title="Define team roster with role-archetype taxonomy" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L3" \
  --description="Implement the TeamRoster fixture and data model. Each team member: user_id, name, title, role_archetype (IC Engineer | Eng Manager | Supply Chain | Product Manager). Populate with 20-30 synthetic AMR team members. Role archetypes are used by Layer 4's 4x8 role-type alignment matrix from section 5.2." \
  --silent)

L3_2=$(bd create \
  --title="Implement workstream registry with channel-to-workstream mapping" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L3" \
  --description="Define 8 workstreams (chassis, drivetrain, thermal, power-systems, sensors, firmware, supply-chain, end-effector) and map each to its Slack channels. Expose: get_workstream(channel) -> str and get_channels(workstream) -> [str]. Channel membership is a seed signal for workstream affinity per section 6.2. Also exposes component-to-workstream mapping used when an atom tags a component like 'motor controller FPGA' and the pipeline must infer workstream." \
  --silent)

L3_3=$(bd create \
  --title="Implement per-workstream phase vector (ADR-004)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L3" \
  --description="Model phase as dict[workstream, Phase] not a project scalar (ADR-004: different subsystems occupy different phases simultaneously). Phases: Concept | EVT | DVT | PVT | MP. Populate from section 6.3: Chassis=DVT, Drivetrain=DVT, Thermal=Late EVT, Power Systems=DVT, Sensors=EVT, Firmware=EVT, End-Effector=Concept. Expose: get_phase(workstream) -> Phase and set_phase(workstream, phase) to support the frontend phase-override demo feature." \
  --silent)

L3_4=$(bd create \
  --title="Define and populate three fully-specified demo personas" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L3" \
  --description="Create three Persona fixture objects per schema in section 6.1: (1) Maya Chen, Senior ME - chassis:1.0, thermal:0.85, drivetrain:0.4, supply-chain:0.3; (2) Supply Chain Lead - supply-chain:1.0, all workstreams 0.4-0.7; (3) Engineering Manager - all workstreams 0.6-0.9, Eng Manager archetype. Include workstream_affinities, phase_context, scoring_weights (default 0.30/0.20/0.20/0.15/0.15), collaborator_graph (3-5 user_ids), and digest_preferences (max_items=25, critical_threshold=0.85)." \
  --silent)

# L3 internal ordering: roster → workstreams → phase vector → personas
bd dep add "$L3_2" "$L3_1"
bd dep add "$L3_3" "$L3_2"
bd dep add "$L3_4" "$L3_3"

echo "    EPIC_L3=$EPIC_L3  L3_1=$L3_1  L3_2=$L3_2  L3_3=$L3_3  L3_4=$L3_4"

# ─── EPIC 6: Layer 4 - Relevance Scoring ─────────────────────────────────────
echo ""
echo "==> Creating Epic 6: Layer 4 - Relevance Scoring"

EPIC_L4=$(bd create \
  --title="Layer 4: Relevance Scoring" \
  --type=epic \
  --priority=1 \
  --description="Implement the five-dimension relevance scoring engine (section 5.2) that produces a per-persona, per-atom composite score. Relevance is relational - the same SPEC_CHANGE atom is critical to the power systems engineer and irrelevant to the enclosure ME (section 5.1). Dimensions: workstream proximity (0.30), role-type alignment (0.20), phase alignment (0.20), urgency (0.15), social signal (0.15). Adaptive weight learning is stubbed per section 5.4 note." \
  --silent)

L4_1=$(bd create \
  --title="Implement Dimension 1: workstream proximity scoring (weight 0.30)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L4" \
  --description="Score = max(persona.workstream_affinities[ws] for ws in [atom.originating] + atom.affected). Uses the persona's affinity vector and the atom's full workstream tag set. This is the strongest signal (0.30 weight): a spec change that affects your workstream scores high even if it originated in a channel you don't follow. The cross-workstream affected tags from L2 extraction are what make this powerful." \
  --silent)

L4_2=$(bd create \
  --title="Implement Dimension 2: role-type alignment matrix (weight 0.20)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L4" \
  --description="Encode the 4x8 role-archetype x atom-type affinity matrix from section 5.2 as a nested dict. Score = matrix[persona.role_archetype][atom.type]. Examples: Supply Chain has 0.9 affinity for DECISION and SPEC_CHANGE; Eng Manager has 0.9 for BLOCKER and RISK; IC Engineer has 0.9 for SPEC_CHANGE and TEST_RESULT in their domain. Default weight 0.20." \
  --silent)

L4_3=$(bd create \
  --title="Implement Dimension 3: phase alignment matrix with per-workstream phase lookup (weight 0.20)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L4" \
  --description="Encode the 5x8 phase x atom-type relevance matrix from section 5.2. Score = max(matrix[get_phase(ws)][atom.type] for ws in atom.affected_workstreams). EVT emphasis: TEST_RESULT=0.9, SPEC_CHANGE=0.9. DVT emphasis: RISK=0.8, vendor/tooling atoms. Because workstreams are in different phases simultaneously (ADR-004), the score is per-workstream. This is the dimension that produces the phase-sensitivity demo effect (Evaluation Criterion 3). Calls L3 get_phase()." \
  --silent)

L4_4=$(bd create \
  --title="Implement Dimension 4: urgency pass-through scoring (weight 0.15)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L4" \
  --description="Urgency is an atom-level property, not persona-specific. Normalize: high=1.0, medium=0.6, low=0.3. Urgency boosts relevance but does not override workstream proximity - an urgent firmware atom is still near-zero relevance for a chassis ME with no firmware involvement. Default weight 0.15." \
  --silent)

L4_5=$(bd create \
  --title="Implement Dimension 5: social signal scoring via collaborator graph (weight 0.15)" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L4" \
  --description="Score based on overlap between atom.key_participants and persona.collaborator_graph. Boost if a collaborator used escalation language ('this is a blocker', reaction count > threshold, @channel). This dimension proxies the informal trust network - if your closest collaborator flagged something, you probably want to know about it too. Default weight 0.15." \
  --silent)

L4_6=$(bd create \
  --title="Implement composite scoring, atom ranking, and critical threshold (0.85)" \
  --type=task \
  --priority=1 \
  --parent="$EPIC_L4" \
  --description="Assemble the full scoring pipeline: for each (atom, persona) pair compute relevance = sum(weight_i * dim_i_score) where weights come from persona.scoring_weights and sum to 1.0. Rank atoms by composite score descending. Flag atoms above critical_threshold (default 0.85) for 'Requires Your Action' section. Top N (default 25) form the digest. Expose score_atoms(atoms: List[Atom], persona: Persona) -> List[ScoredAtom] sorted by score." \
  --silent)

# L4 internal: all 5 dimensions are independent of each other; composite score needs all 5
bd dep add "$L4_6" "$L4_1"
bd dep add "$L4_6" "$L4_2"
bd dep add "$L4_6" "$L4_3"
bd dep add "$L4_6" "$L4_4"
bd dep add "$L4_6" "$L4_5"

echo "    EPIC_L4=$EPIC_L4  L4_1=$L4_1  L4_2=$L4_2  L4_3=$L4_3  L4_4=$L4_4  L4_5=$L4_5  L4_6=$L4_6"

# ─── EPIC 7: Layer 5 - Digest Generation ─────────────────────────────────────
echo ""
echo "==> Creating Epic 7: Layer 5 - Digest Generation"

EPIC_L5=$(bd create \
  --title="Layer 5: Digest Generation" \
  --type=epic \
  --priority=2 \
  --description="Implement the generation LLM pass (section 7.1-7.2) that converts ranked, scored atoms into natural-language digest prose. The generated digest has four priority-tiered sections: Requires Your Action (score >= 0.85, max 5 items), Decisions and Changes, Progress and Risks, Broader Context. Tone: briefing not newsletter - terse, specific, scannable. Each item: bold headline + 1-2 sentence context + source link back to Slack thread." \
  --silent)

L5_1=$(bd create \
  --title="Design generation prompt: briefing tone, four-section structure, no editorializing" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L5" \
  --description="Write the digest generation system prompt per section 7.2. Three tone instructions: (1) Briefing not newsletter - terse, specific, information-dense, like a competent chief of staff; (2) Scannable format - bold headline + 1-2 sentence context + source reference per item, scannable in 30 seconds; (3) No editorializing - report what happened, not whether the decision was good. The moment the digest starts adding opinions it loses engineering team trust." \
  --silent)

L5_2=$(bd create \
  --title="Implement per-persona digest generation runner" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L5" \
  --description="Build the DigestGenerator class: for each persona, take the ranked ScoredAtom list from Layer 4, cluster by originating workstream, pass clusters to Anthropic API with generation prompt + persona context. Parse LLM response into List[DigestSection] objects: section_type (requires_action | decisions_changes | progress_risks | broader_context), items (each with headline, context, source_url). Respect persona.digest_preferences.include_broader_context flag." \
  --silent)

L5_3=$(bd create \
  --title="Implement digest assembly and GET /digest endpoint with phase-override support" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_L5" \
  --description="Wire together the full pipeline into GET /digest/{persona_id}. Implement GET /digest/{persona_id}?phase_override={ws}:{phase} - temporarily calls L3 set_phase(ws, phase) before scoring, enabling the frontend phase-transition toggle demo. Response model: DigestResponse {persona, generated_at, sections: List[DigestSection]}. This endpoint is what the frontend calls for every persona switch and phase toggle (Evaluation Criterion 3 depends on this)." \
  --silent)

# L5 internal ordering: prompt → runner → endpoint
bd dep add "$L5_2" "$L5_1"
bd dep add "$L5_3" "$L5_2"

echo "    EPIC_L5=$EPIC_L5  L5_1=$L5_1  L5_2=$L5_2  L5_3=$L5_3"

# ─── EPIC 8: Frontend UI ──────────────────────────────────────────────────────
echo ""
echo "==> Creating Epic 8: Frontend UI"

EPIC_UI=$(bd create \
  --title="Frontend UI: Persona Switcher, Digest Display, Phase Toggle" \
  --type=epic \
  --priority=2 \
  --description="Build the React frontend that demonstrates the core thesis interactively (section 9.1): switch personas and watch the digest change; toggle a workstream's phase and watch content shift. The UI must be a readable, professionally styled digest - not a dev debug panel. Four components: persona selector, sectioned digest display, phase-transition toggle, and pipeline run trigger." \
  --silent)

UI_1=$(bd create \
  --title="Build persona selector: tab-based nav for three demo personas" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_UI" \
  --description="Render a top-nav tab bar with the three demo personas (Maya Chen ME, SC Lead, EM). Clicking a tab calls GET /digest/{persona_id} and triggers a full re-render of the digest panel. Show persona name, title, and top 2-3 workstream affinities as subtitle so the evaluator understands who they're looking at. Default to ME persona on load." \
  --silent)

UI_2=$(bd create \
  --title="Build sectioned digest display with visual hierarchy and source links" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_UI" \
  --description="Render the four digest sections with distinct visual treatment: Requires Your Action in red/amber with attention flag icon; Decisions and Changes in yellow/warning; Progress and Risks in blue; Broader Context in grey/muted. Each digest item: bold headline, context paragraph, source chip (channel name + reply count) that references the thread. Show empty state gracefully. Loading skeleton while /digest request is in flight." \
  --silent)

UI_3=$(bd create \
  --title="Build phase-transition toggle demo panel" \
  --type=task \
  --priority=2 \
  --parent="$EPIC_UI" \
  --description="Add a collapsible 'Demo Controls' panel (collapsed by default, visually distinguished as a dev tool). Inside: workstream dropdown + phase dropdown for each workstream, and an Apply Override button. On apply, calls GET /digest/{persona_id}?phase_override={ws}:{phase} and re-renders. Show a banner: 'Viewing with [Thermal: EVT → DVT] override'. Directly demonstrates Evaluation Criterion 3 (phase sensitivity) to the reviewer." \
  --silent)

UI_4=$(bd create \
  --title="Add pipeline run trigger with progress indicator" \
  --type=task \
  --priority=3 \
  --parent="$EPIC_UI" \
  --description="Add a 'Re-run Pipeline' button in the demo controls panel that calls POST /pipeline/run. Show a progress bar with status text (Ingesting messages... Extracting atoms... Scoring... Generating digests...). Poll GET /pipeline/status until complete, then refresh the current digest view. Demonstrates the pipeline is live and not pre-canned responses." \
  --silent)

# UI internal: display component must exist before persona tabs and phase toggle wire it up
bd dep add "$UI_2" "$UI_1"
bd dep add "$UI_3" "$UI_2"
bd dep add "$UI_4" "$UI_2"

echo "    EPIC_UI=$EPIC_UI  UI_1=$UI_1  UI_2=$UI_2  UI_3=$UI_3  UI_4=$UI_4"

# ─── STANDALONE: Prune catalyst-ui-kit ───────────────────────────────────
echo ""
echo "==> Creating standalone task: Prune catalyst-ui-kit"

PRUNE_CATALYST=$(bd create \
  --title="Aggressively prune catalyst-ui-kit to ONLY include used components" \
  --type=task \
  --priority=2 \
  --description="Once all frontend development is complete, audit every catalyst-ui-kit import across the React codebase. Remove all unused component exports, CSS, and assets from the bundled catalyst-ui-kit dependency. Tree-shake or manually strip any component not actively rendered in the final UI. Goal: minimize bundle size and eliminate dead code from the kit. This MUST wait until all frontend UI work (Epic 8) is finished so the full set of used components is known." \
  --silent)

# Must wait until all frontend work is done
bd dep add "$PRUNE_CATALYST" "$EPIC_UI"

echo "    PRUNE_CATALYST=$PRUNE_CATALYST"

# ─── STANDALONE: Abstract config into YAML files ────────────────────────
echo ""
echo "==> Creating standalone task: Abstract config into YAML files"

YAML_CONFIG=$(bd create \
  --title="Abstract as much config as possible into .yml files" \
  --type=task \
  --priority=2 \
  --description="Audit the entire codebase for hardcoded configuration values (channel lists, roster data, workstream phase mappings, scoring weights, prompt templates, API URLs, thresholds, etc.) and extract them into .yml config files. Use a config/ directory at the project root. Load YAML at startup and inject into the relevant services. This reduces code churn for config changes and makes the system easier to tune for demos. Cover: channel registry, team roster, workstream phases, scoring dimension weights, digest preferences defaults, role-type alignment matrix, phase-alignment matrix, prompt templates." \
  --silent)

# Can be done anytime after the core pipeline is built
bd dep add "$YAML_CONFIG" "$EPIC_L5"

echo "    YAML_CONFIG=$YAML_CONFIG"

# ─── EPIC 9: Evaluation & Demo Validation ────────────────────────────────────
echo ""
echo "==> Creating Epic 9: Evaluation & Demo Validation"

EPIC_EVAL=$(bd create \
  --title="Evaluation and Demo Validation" \
  --type=epic \
  --priority=3 \
  --description="Validate the three success criteria from section 10.1 against the running prototype: (1) Differential relevance - same data, meaningfully different digests for different personas; (2) Signal surfacing - buried cross-workstream signals appear in the right persona's digest; (3) Phase sensitivity - phase-toggle produces visible digest content change. These tests serve double duty as integration tests and reviewer demo scripts." \
  --silent)

EVAL_1=$(bd create \
  --title="Validate Criterion 1: differential relevance across three personas" \
  --type=task \
  --priority=3 \
  --parent="$EPIC_EVAL" \
  --description="Run all three personas through the full pipeline and assert non-overlap in top digest items. ME digest must rank the torque spec change and chassis test result highly. SC Lead digest must rank the material change and vendor lead time risk highly. EM digest must rank blockers and cross-workstream risks highly. If all three digests look similar, workstream proximity or role-type alignment scoring is broken. Write a pytest test asserting these by atom type and originating workstream." \
  --silent)

EVAL_2=$(bd create \
  --title="Validate Criterion 2: three buried signals surface in correct persona digests" \
  --type=task \
  --priority=3 \
  --parent="$EPIC_EVAL" \
  --description="Assert all three planted signals from the dataset appear in the correct persona digests: (1) magnesium housing implicit decision appears in SC Lead digest under Decisions and Changes (checks cross-workstream affected tagging worked); (2) thermal interface material root cause appears in both ME and Thermal owner digests (checks affected workstream propagation from #testing); (3) FPGA lead time appears in SC Lead digest despite not originating in a channel they follow. Missing any of these means extraction or scoring is failing its core mission." \
  --silent)

EVAL_3=$(bd create \
  --title="Validate Criterion 3: phase-toggle produces visible digest content shift" \
  --type=task \
  --priority=3 \
  --parent="$EPIC_EVAL" \
  --description="Test phase sensitivity via the /digest endpoint's phase_override parameter. For Maya Chen ME persona: call /digest/maya with no override (Thermal=Late EVT) and with phase_override=thermal:DVT. Assert that the DVT digest shifts away from DECISION/SPEC_CHANGE atoms toward RISK, TEST_RESULT, and STATUS_UPDATE atoms for the thermal workstream (per the 5x8 phase-alignment matrix in section 5.2). At least 2 items should differ in position or section between the two responses." \
  --silent)

echo "    EPIC_EVAL=$EPIC_EVAL  EVAL_1=$EVAL_1  EVAL_2=$EVAL_2  EVAL_3=$EVAL_3"

# ─── INTER-EPIC DEPENDENCIES ─────────────────────────────────────────────────
echo ""
echo "==> Adding inter-epic pipeline dependencies"

# Tooling must be fully configured before Foundation can start
bd dep add "$EPIC_INFRA" "$EPIC_TOOL"

# Foundation unblocks all other epics
bd dep add "$EPIC_DATA"  "$EPIC_INFRA"
bd dep add "$EPIC_L1"    "$EPIC_INFRA"
bd dep add "$EPIC_L2"    "$EPIC_INFRA"
bd dep add "$EPIC_L3"    "$EPIC_INFRA"
bd dep add "$EPIC_L4"    "$EPIC_INFRA"
bd dep add "$EPIC_L5"    "$EPIC_INFRA"
bd dep add "$EPIC_UI"    "$EPIC_INFRA"

# Synthetic data must be fully authored before ingestion layer processes it
bd dep add "$EPIC_L1"    "$EPIC_DATA"

# Ingestion output (ContextWindows) feeds extraction
bd dep add "$EPIC_L2"    "$EPIC_L1"

# Relevance scoring needs both: extracted atoms AND the world model
bd dep add "$EPIC_L4"    "$EPIC_L2"
bd dep add "$EPIC_L4"    "$EPIC_L3"

# Digest generation consumes ranked atoms from relevance scoring
bd dep add "$EPIC_L5"    "$EPIC_L4"

# Frontend renders digests from the generation API
bd dep add "$EPIC_UI"    "$EPIC_L5"

# Evaluation requires the full stack to be running end-to-end
bd dep add "$EPIC_EVAL"  "$EPIC_UI"

# ─── CROSS-EPIC LEAF-LEVEL DEPENDENCIES ──────────────────────────────────────
echo ""
echo "==> Adding cross-epic leaf-level dependencies"

# INFRA_1 (FastAPI backend) needs the full toolchain passing first
bd dep add "$INFRA_1" "$TOOL_6"

# L1 message loader reads from the fixture store
bd dep add "$L1_1"   "$INFRA_3"

# L2 atom schema extends the stub model from backend initialization
bd dep add "$L2_1"   "$INFRA_1"

# L3 roster loader reads from the fixture store
bd dep add "$L3_1"   "$INFRA_3"

# L4 phase alignment calls L3 get_phase() - hard runtime dependency
bd dep add "$L4_3"   "$L3_3"

# L4 workstream proximity uses persona affinity vectors from L3 personas
bd dep add "$L4_1"   "$L3_4"

# L4 role-type matrix uses persona.role_archetype from L3 roster
bd dep add "$L4_2"   "$L3_1"

# L4 social signal uses persona.collaborator_graph from L3 personas
bd dep add "$L4_5"   "$L3_4"

# L5 endpoint calls L3 set_phase() for the phase-override demo feature
bd dep add "$L5_3"   "$L3_3"

# Eval criterion 2 (buried signals) needs the extraction runner to have produced atoms
bd dep add "$EVAL_2" "$L2_3"

# Eval criterion 3 (phase sensitivity) needs the phase alignment dimension
bd dep add "$EVAL_3" "$L4_3"

# Eval criterion 1 (differential relevance) needs full composite scoring wired
bd dep add "$EVAL_1" "$L4_6"

# ─── STANDALONE: Comprehensive README ────────────────────────────────────
echo ""
echo "==> Creating standalone task: Write comprehensive README.md"

README=$(bd create \
  --title="Write comprehensive README.md once all other issues are complete" \
  --type=task \
  --priority=3 \
  --description="Write a thorough README.md covering: project overview and thesis (context-aware daily digest for robotics teams), architecture diagram (5-layer pipeline), quick start instructions (uv sync, run backend, run frontend), API endpoints, the three demo personas and what to look for, how to run quality gates, design decisions and trade-offs, and evaluation criteria from section 10.1. This MUST wait until all development and evaluation work is finished so the README accurately reflects the final state of the project." \
  --silent)

# Must wait until evaluation is done (all development complete)
bd dep add "$README" "$EPIC_EVAL"

echo "    README=$README"

# ─── STANDALONE: Integrate interrogate into quality gates ─────────────────────
echo ""
echo "==> Creating standalone task: Integrate interrogate into quality gates"

INTERROGATE=$(bd create \
  --title="Integrate interrogate docstring coverage into quality gates" \
  --type=task \
  --priority=3 \
  --description="Add interrogate to the dev dependency group and integrate it into scripts/quality-gates.sh as a new gate. Configure in pyproject.toml under [tool.interrogate] to match existing project conventions: style='google' (matches [tool.ruff.lint.pydocstyle] convention), line-length 99 (matches [tool.ruff] line-length), --fail-under=95, ignore-init-method=true, ignore-init-module=true, ignore-magic=true, ignore-semiprivate=true, ignore-private=true, ignore-nested-functions=true, ignore-nested-classes=true, ignore-property-decorators=true, ignore-setters=true, ignore-overloaded-functions=true, color=true, verbose=1, exclude=['tests/', 'docs/', '.venv/']. Add a 7th quality gate to scripts/quality-gates.sh that runs 'uv run interrogate src/ --fail-under 95'. This MUST run after README is written so that all public API docstrings exist." \
  --silent)

# Must wait until README is done (all docstrings finalized)
bd dep add "$INTERROGATE" "$README"

echo "    INTERROGATE=$INTERROGATE"

# ─── STANDALONE: Multistage Dockerfiles and Docker Compose ───────────────────
echo ""
echo "==> Creating standalone task: Multistage Dockerfiles and Docker Compose"

DOCKER=$(bd create \
  --title="Build multistage Dockerfiles and Docker Compose for local development" \
  --type=task \
  --priority=3 \
  --description="Create multistage Dockerfiles for each part of the application: (1) backend/Dockerfile - Python FastAPI backend with uv for dependency management, multistage build (builder stage installs deps, runtime stage copies venv and src), (2) frontend/Dockerfile - Node/React frontend with multistage build (builder stage runs npm build, runtime stage serves with nginx or node), (3) docker-compose.yml - Orchestrates all services for local development: backend (port 8000), frontend (port 3000), with environment variables for ANTHROPIC_API_KEY, health checks, volume mounts for development hot-reload, and proper networking between services. Each Dockerfile should use slim/alpine base images, non-root users, .dockerignore files, and follow Docker best practices for layer caching. This MUST wait until README is written so the Docker setup can reference final project structure." \
  --silent)

# Must wait until README is done (project structure finalized)
bd dep add "$DOCKER" "$README"

echo "    DOCKER=$DOCKER"

# ─── STANDALONE: Sphinx documentation site ───────────────────────────────────
echo ""
echo "==> Creating standalone task: Build Sphinx documentation site"

SPHINX_DOCS=$(bd create \
  --title="Build Sphinx documentation site including design-document.rst" \
  --type=task \
  --priority=3 \
  --description="Set up Sphinx documentation for the project. Add sphinx, sphinx-rtd-theme, and sphinx-autodoc-typehints to dev dependencies. Create docs/ directory with conf.py, index.rst, and Makefile. Configure autodoc to generate API reference from src/evercurrent/ docstrings (Google style via napoleon extension). Include design-document.rst in the generated site via a toctree entry (symlink or copy into docs/). Configure sphinx-rtd-theme for clean presentation. Add a 'make docs' or 'uv run sphinx-build' command. The generated site should include: project overview, full API reference auto-generated from code docstrings, the design document, and architecture diagrams if present. This MUST wait until interrogate has been integrated (ensuring docstring coverage is enforced before docs are generated)." \
  --silent)

# Must wait until interrogate is done (docstring coverage enforced)
bd dep add "$SPHINX_DOCS" "$INTERROGATE"

echo "    SPHINX_DOCS=$SPHINX_DOCS"

# ─── STANDALONE: GitHub Actions CI/CD Pipeline ──────────────────────────────
echo ""
echo "==> Creating standalone task: GitHub Actions CI/CD Pipeline"

GH_ACTIONS=$(bd create \
  --title="Create GitHub Actions CI/CD pipeline with quality gates, security scanning, and SBOM" \
  --type=task \
  --priority=3 \
  --description="Create .github/workflows/quality-gate.yml modeled off the local scripts/quality-gates.sh and the metalog_jax reference pipeline. Jobs: (1) quality-gates - ruff lint, ruff format, ty check, pytest with coverage >=90%, radon cc <=8, radon mi A rating, interrogate >=95%; (2) license-check - pip-licenses with allowed list (MIT, BSD, Apache, PSF, ISC, Unlicense, Public Domain, CC0, Zlib, Mozilla, 0BSD); (3) semgrep - scan with p/python, p/security-audit, p/owasp-top-ten, p/cwe-top-25, p/secrets configs, fail on ERROR severity; (4) bandit - scan src/ with medium severity/confidence, fail on high; (5) sbom - generate CycloneDX and SPDX SBOMs with syft, scan with grype, fail on critical vulnerabilities; (6) docs - build Sphinx documentation site and deploy as artifact. Trigger on push to main and pull_request. Use astral-sh/setup-uv@v4 for uv. Upload all scan results and SBOM reports as artifacts." \
  --silent)

# Must wait until Sphinx docs are done (all local tools configured)
bd dep add "$GH_ACTIONS" "$SPHINX_DOCS"

echo "    GH_ACTIONS=$GH_ACTIONS"

# ─── STANDALONE: Makefile for local CI commands ─────────────────────────────
echo ""
echo "==> Creating standalone task: Makefile for local CI commands"

MAKEFILE=$(bd create \
  --title="Create Makefile that runs all local commands matching GitHub Actions jobs" \
  --type=task \
  --priority=3 \
  --description="Create a Makefile at the project root that provides local equivalents of every GitHub Actions pipeline job. Targets: (1) make lint - ruff check src/ tests/; (2) make format - ruff format --check src/ tests/; (3) make typecheck - ty check src/; (4) make test - pytest with coverage >=90%; (5) make complexity - radon cc and mi checks; (6) make interrogate - interrogate src/ --fail-under 95; (7) make license-check - pip-licenses with allowed list; (8) make semgrep - semgrep scan with security configs; (9) make bandit - bandit scan src/; (10) make sbom - syft + grype scan; (11) make docs - sphinx-build docs; (12) make quality - runs all quality gates (lint, format, typecheck, test, complexity, interrogate); (13) make security - runs all security gates (license-check, semgrep, bandit, sbom); (14) make all - runs quality + security + docs; (15) make ci - mirrors the full GitHub Actions pipeline locally. Each target should use 'uv run' prefix for Python tools. Include .PHONY declarations. This MUST wait until the GitHub Actions pipeline issue is closed so the Makefile accurately mirrors the CI jobs." \
  --silent)

# Must wait until GitHub Actions pipeline is done
bd dep add "$MAKEFILE" "$GH_ACTIONS"

echo "    MAKEFILE=$MAKEFILE"

# ─── STANDALONE: Next Steps document ────────────────────────────────────────
echo ""
echo "==> Creating standalone task: Write next-steps.rst"

NEXT_STEPS=$(bd create \
  --title="Write next-steps.rst covering follow-on work, stakeholder questions, and production path" \
  --type=task \
  --priority=3 \
  --description="Write docs/next-steps.rst documenting recommended follow-on work after the prototype is delivered. Include in the Sphinx toctree. Sections: (1) Stakeholder Questions - expand section 11 of design-document.rst: IP classification for cloud vs on-prem LLM, PM tool integration for automated phase detection, multi-source ingestion beyond Slack, user interview findings, organizational structure clarity; (2) Live Data Integration - replacing static synthetic dataset with Slack OAuth bot, real-time message ingestion, webhook vs polling, message deduplication, handling edits/deletes; (3) Configuration Interface - web-based UI for editing YAML configs, real-time preview of scoring changes, admin panel for managing personas; (4) Adaptive Feedback Loop - implementing the stubbed feedback mechanism (section 5.4), user implicit signals, weight learning, A/B testing; (5) Production Hardening - persistent storage, auth, observability, error handling, rate limiting, caching; (6) Scaling Path - batch to stream (Kafka), parallelized extraction, searchable atom index; (7) Additional Integrations - PLM/ERP/PM tool connectors, email, CAD comments, ticket sync; (8) Phase Transition Detection - automated inference from language patterns; (9) Evaluation in Production - section 10.2 metrics; (10) Security and Compliance - on-prem inference, data retention, audit logging, SOC2." \
  --silent)

# Must wait until Makefile is done (all tooling finalized)
bd dep add "$NEXT_STEPS" "$MAKEFILE"

echo "    NEXT_STEPS=$NEXT_STEPS"

# ─── SVG Architecture Diagram ────────────────────────────────────────────────
echo ""
echo "==> Creating SVG Architecture Diagram issue"

SVG_ARCH=$(bd create \
  --title="Create static SVG architecture diagram for README and docs" \
  --type=task \
  --priority=2 \
  --description="Replace the ASCII/text architecture diagram in README.md (Architecture section) and docs/design-document.rst Section 3.1 Architecture Overview with a proper static SVG diagram. Create docs/_static/ folder and place the SVG there. Update README.md and design-document.rst to reference the SVG instead of inline text diagrams." \
  --silent)

# Must wait until Next Steps is done (all docs finalized)
bd dep add "$SVG_ARCH" "$NEXT_STEPS"

echo "    SVG_ARCH=$SVG_ARCH"

# ─── Model-Agnostic LLM Client ──────────────────────────────────────────────
echo ""
echo "==> Creating Model-Agnostic LLM Client issue"

LLM_CLIENT=$(bd create \
  --title="Refactor LLM client to model-agnostic harness supporting Anthropic, Google, and OpenAI" \
  --type=feature \
  --priority=2 \
  --description="Replace all direct Anthropic client references with a model-agnostic client abstraction. Currently the Anthropic SDK client is hardcoded across 4 source modules and 4 test modules.

Source files to refactor (type annotations + imports):
- src/evercurrent/extraction/runner.py: from anthropic import Anthropic, __init__(self, client: Anthropic)
- src/evercurrent/extraction/validation.py: from anthropic import Anthropic, validate_atoms(client: Anthropic), validate_single_atom(client: Anthropic)
- src/evercurrent/generation/runner.py: from anthropic import Anthropic, __init__(self, client: Anthropic)
- src/evercurrent/generation/assembler.py: from anthropic import Anthropic, __init__(self, client: Anthropic)

Test files with Anthropic-specific mocks (MagicMock simulating Anthropic response shape):
- tests/test_extraction/test_runner.py: _mock_api_response(), 12+ MagicMock client instances
- tests/test_extraction/test_validation.py: _mock_validation_response(), 10+ MagicMock client instances
- tests/test_generation/test_runner.py: _mock_api_response(), 14+ MagicMock client instances
- tests/test_generation/test_assembler.py: 7+ MagicMock client instances

Implementation plan:
1. Create src/evercurrent/llm/ package with a Protocol or ABC defining the common client interface (messages.create compatible)
2. Implement concrete adapters for Anthropic, Google (Gemini), and OpenAI
3. Add provider selection to config/pipeline.yml
4. Update all 4 source modules to accept the abstract type
5. Update all 4 test files to mock against the abstract interface
6. Write tests for the LLM client abstraction itself in tests/test_llm/
7. Add a section to docs/next-steps.rst about on-prem/self-hosted model support (vLLM, Ollama, TGI) for data-sensitive deployments" \
  --silent)

# Must wait until SVG diagram is done
bd dep add "$LLM_CLIENT" "$SVG_ARCH"

echo "    LLM_CLIENT=$LLM_CLIENT"

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
echo ""
echo "✓ Epic hierarchy created successfully."
echo ""
echo "  bd ready                        - see what to start (Foundation tasks will be first)"
echo "  bd dep tree \$EPIC_INFRA          - visualize Foundation epic"
echo "  bd dep tree \$EPIC_L4             - visualize Scoring epic dependencies"
echo "  bd stats                        - project overview"
echo ""
echo "  Epic IDs:"
echo "    E0 Tooling:           $EPIC_TOOL"
echo "    E1 Foundation:        $EPIC_INFRA"
echo "    E2 Synthetic Data:    $EPIC_DATA"
echo "    E3 Layer 1 Ingest:    $EPIC_L1"
echo "    E4 Layer 2 Extract:   $EPIC_L2"
echo "    E5 Layer 3 Context:   $EPIC_L3"
echo "    E6 Layer 4 Scoring:   $EPIC_L4"
echo "    E7 Layer 5 Digest:    $EPIC_L5"
echo "    E8 Frontend UI:       $EPIC_UI"
echo "    E9 Evaluation:        $EPIC_EVAL"
echo "    Prune Catalyst:      $PRUNE_CATALYST"
echo "    YAML Config:         $YAML_CONFIG"
echo "    README:              $README"
echo "    Interrogate:         $INTERROGATE"
echo "    Docker:              $DOCKER"
echo "    Sphinx Docs:         $SPHINX_DOCS"
echo "    GH Actions:          $GH_ACTIONS"
echo "    Makefile:            $MAKEFILE"
echo "    Next Steps:          $NEXT_STEPS"
echo "    SVG Arch Diagram:    $SVG_ARCH"
echo "    LLM Client:         $LLM_CLIENT"

# ─── CR-1: WIRE PIPELINE END-TO-END ─────────────────────────────────────────
WIRE_PIPELINE=$(bd create \
  --title="Wire pipeline end-to-end: connect Ingestion → Extraction → Scoring → Generation in API endpoints" \
  --type=bug \
  --priority=0 \
  --description="CR-1 from REVIEW.md. /pipeline/run returns stub. /digest/{persona_id} returns empty sections. DigestAssembler exists but is never called from any endpoint. The five layers are built and tested in isolation but never composed into a working flow. Without this, the system cannot demo its primary job. Wire DigestAssembler into /digest endpoint and implement /pipeline/run to trigger extraction." \
  --silent)
echo "    Wire Pipeline:      $WIRE_PIPELINE"

# ─── ENV VAR AUDIT & .env.sample ────────────────────────────────────────────
ENV_AUDIT=$(bd create \
  --title="Audit all OS env var references and create .env.sample at repo root" \
  --type=task \
  --priority=1 \
  --description="Deep-reason through the entire codebase to find every os.environ, os.getenv, and any config loader that reads environment variables. Catalog each var with its purpose, default value (if any), and which module references it. Then create a .env.sample file at repo root documenting all required and optional env vars with placeholder values and comments." \
  --silent)
echo "    Env Var Audit:      $ENV_AUDIT"

# ─── CR-2: PERSISTENT KNOWLEDGE GRAPH ──────────────────────────────────────
KNOWLEDGE_GRAPH=$(bd create \
  --title="Persistent knowledge graph - replace stateless batch architecture with graph-backed atom storage" \
  --type=feature \
  --priority=1 \
  --description="CR-2: The system recomputes everything per request. Atoms, scores, digests are ephemeral. Cannot answer temporal queries ('what changed since yesterday?', 'is this blocker a pattern?'). Implement Neo4j Community Edition + APOC as a Docker Compose service with a Python graph client module. Persist atoms after pipeline extraction. Enable Cypher-based temporal queries. Trade study concluded: Neo4j CE scored 4.30/5.00, beating Memgraph (3.85), FalkorDB (3.75), and Apache AGE (2.35) on Cypher completeness, Python driver maturity, prototype fit, and developer familiarity." \
  --design="Neo4j CE + APOC via Docker Compose. neo4j Python driver v6.x async API. Graph schema: Atom nodes with EXTRACTED_FROM->Channel, ORIGINATES_IN->Workstream, AFFECTS->Workstream, INVOLVES->Participant edges. All edges timestamped. MERGE for idempotent upserts. APOC temporal functions for date math." \
  --acceptance="1. Neo4j service in docker-compose.yml with health check. 2. Python graph client at src/evercurrent/graph/client.py with async connect/persist/query. 3. Atoms persisted after pipeline extraction. 4. Temporal query: atoms_since(datetime). 5. Tests covering graph client CRUD and temporal queries." \
  --silent)
echo "    Knowledge Graph:    $KNOWLEDGE_GRAPH"

# ─── CR-1.4: ASYNC PIPELINE ─────────────────────────────────────────────────
ASYNC_PIPELINE=$(bd create \
  --title="Async pipeline - replace synchronous serial LLM calls with concurrent execution" \
  --type=feature \
  --priority=2 \
  --description="CR-1.4: FastAPI endpoints are async def but the entire pipeline is synchronous. LLM calls process windows sequentially - 50+ serial round-trips at ~2s each. The pipeline needs to use async/await with concurrent execution (asyncio.gather or similar) to process extraction windows in parallel, dramatically reducing end-to-end latency." \
  --design="Convert Pipeline methods to async. Use asyncio.gather/TaskGroup for concurrent LLM calls within extraction. Keep FastAPI endpoints async (already are). Ensure the LLM client interface supports async calls. Add concurrency limit to avoid rate-limiting." \
  --acceptance="1. Pipeline extraction processes windows concurrently via asyncio. 2. LLM client exposes async interface. 3. FastAPI endpoints await pipeline directly (no sync-to-async bridge). 4. All existing tests pass. 5. All 7 quality gates pass." \
  --silent)
echo "    Async Pipeline:     $ASYNC_PIPELINE"

# ─── CR-3.1: STRUCTURED OUTPUT ENFORCEMENT ──────────────────────────────────
STRUCTURED_OUTPUT=$(bd create \
  --title="Structured output enforcement - replace json.loads() with instructor + Pydantic models" \
  --type=feature \
  --priority=1 \
  --description="CR-3.1: Both extraction and generation rely on json.loads() as the only parse step. When the LLM returns markdown-fenced JSON or adds explanatory text, the pipeline silently drops the entire response. This is the #1 production ML engineering concern - every major LLM occasionally returns non-JSON responses. Silent data loss is unacceptable." \
  --design="Add instructor library to pyproject.toml. Replace raw json.loads() parsing in extraction runner and generation runner with instructor-patched clients that return typed Pydantic models directly. Reuse existing Atom and DigestSection Pydantic models as the response schemas. Support both sync and async clients. Instructor handles retries, markdown fence stripping, and schema validation automatically." \
  --acceptance="1. instructor added to pyproject.toml dependencies. 2. Extraction runner uses instructor to get list[Atom] directly from LLM. 3. Generation runner uses instructor to get structured DigestSection responses. 4. Both sync and async paths use instructor. 5. No more silent data loss from malformed JSON. 6. All existing tests continue to pass. 7. All 7 quality gates pass." \
  --silent)
echo "    Structured Output:  $STRUCTURED_OUTPUT"

# ─── CR-4.1: SCORING CALIBRATION ────────────────────────────────────────────
SCORING_CALIBRATION=$(bd create \
  --title="Calibrate scoring dimensions - normalize distributions across five dimensions" \
  --type=bug \
  --priority=2 \
  --description="CR-4.1: The five scoring dimensions (workstream_proximity, role_type_alignment, phase_alignment, urgency, social_signal) have different distributions. Discrete 4-value dimensions (urgency) vs continuous dimensions create unequal influence. The relative influence of each dimension doesn't match the stated persona weights. Urgency and social_signal have 0.3-0.5 step sizes that dominate ranking decisions regardless of weight configuration. Need to normalize distributions so persona weights actually control relative influence." \
  --design="Normalize each scoring dimension to [0,1] continuous range before applying persona weights. Options: (1) min-max normalization per dimension, (2) z-score normalization, (3) rank-based normalization. Urgency mapping needs finer granularity than current 4-value discrete (critical=1.0, high=0.7, medium=0.4, low=0.1). Social signal similarly needs smoother distribution. After normalization, verify that changing a persona weight actually shifts ranking outcomes proportionally." \
  --acceptance="1. All five scoring dimensions produce values in [0,1] continuous range. 2. Changing a persona weight by X% shifts that dimension's contribution by ~X%. 3. No single dimension dominates ranking regardless of weight config. 4. Existing test assertions updated to reflect calibrated scores. 5. All 7 quality gates pass." \
  --silent)
echo "    Scoring Calibration: $SCORING_CALIBRATION"

# ─── VULTURE DEAD CODE DETECTION ────────────────────────────────────────────
VULTURE=$(bd create \
  --title="Add vulture for dead code detection - integrate into quality gates and remove all dead code" \
  --type=task \
  --priority=2 \
  --description="Add vulture to the project toolchain and iteratively remove ALL dead code from the codebase. Vulture statically analyzes Python to find unused functions, variables, imports, classes, and attributes. Integrate into pyproject.toml (dependency + config), scripts/quality-gates.sh (as a gate), GitHub Actions CI pipeline, and Makefile. Then run vulture iteratively - fix findings, re-run, repeat until clean." \
  --design="1. Add vulture to dev dependencies in pyproject.toml. 2. Configure vulture in pyproject.toml ([tool.vulture] section) with min_confidence=80 and a whitelist file for false positives (e.g. Pydantic model_config, pytest fixtures, __all__ exports). 3. Add vulture gate to scripts/quality-gates.sh. 4. Add vulture step to GitHub Actions workflow. 5. Add vulture target to Makefile. 6. Run vulture iteratively: review each finding, remove genuine dead code, add confirmed false positives to whitelist. Repeat until zero findings." \
  --acceptance="1. vulture added to pyproject.toml dev dependencies. 2. vulture configured in pyproject.toml with whitelist for false positives. 3. vulture runs as a quality gate in scripts/quality-gates.sh. 4. vulture runs in GitHub Actions CI pipeline. 5. vulture target added to Makefile. 6. All dead code removed from codebase. 7. vulture passes with zero findings. 8. All 7 existing quality gates still pass." \
  --silent)
echo "    Vulture:            $VULTURE"

# ─── CR-3.2: TWO-STAGE EXTRACTION ───────────────────────────────────────────
TWO_STAGE=$(bd create \
  --title="Two-stage extraction - split monolithic prompt into coarse extract then enrich" \
  --type=feature \
  --priority=2 \
  --description="CR-3.2: The 88-line extraction prompt asks the LLM to do too much in one pass: extract events, classify type, assign confidence, identify participants, tag workstreams, determine urgency, assess phase relevance, and detect implicit decisions. This cognitive overload degrades quality on every dimension simultaneously. Split into a two-stage pipeline: Stage 1 (coarse extract) identifies events and produces minimal atoms. Stage 2 (enrich) takes each coarse atom and adds confidence, workstream tags, urgency, phase relevance, and implicit decision detection." \
  --design="1. Research optimal task decomposition for LLM extraction. 2. Design Stage 1 prompt: focused on event identification - type, summary, detail, source, key_participants only. Simpler schema = higher recall. 3. Design Stage 2 prompt(s): enrichment passes adding confidence, workstreams, urgency, phase_relevance. Could be single enrich prompt or parallel micro-prompts per dimension. 4. Update ExtractionRunner to chain stages: extract → enrich → merge into final Atom. 5. Preserve async concurrency - Stage 2 enrichments can run in parallel. 6. Use instructor structured output for both stages. 7. Define intermediate Pydantic models for Stage 1 output (CoarseAtom) distinct from final Atom." \
  --acceptance="1. Extraction split into two distinct LLM stages with separate prompts. 2. Stage 1 prompt focused on event identification only. 3. Stage 2 enriches with metadata (confidence, workstreams, urgency, phase). 4. Final Atom output matches existing schema - downstream pipeline unchanged. 5. Both stages use instructor structured output. 6. Async runner processes Stage 2 enrichments concurrently. 7. All existing tests updated or replaced. 8. All 7 quality gates pass." \
  --silent)
echo "    Two-Stage Extract:  $TWO_STAGE"

# ─── SLACK API-SHAPED DATASET FIXTURE ────────────────────────────────────────
SLACK_FIXTURE=$(bd create \
  --title="Restructure dataset to load from Slack-API-shaped static JSON fixture" \
  --type=feature \
  --priority=2 \
  --description="Deep research the Slack Python SDK (https://docs.slack.dev/messaging/retrieving-messages/) and restructure src/evercurrent/dataset/messages.py to load from a flat static .json file that EXACTLY matches the Slack API response shape as of March 2026. Current synthetic dataset uses an ad-hoc format. The fixture should mirror conversations.history and conversations.replies schemas - ts, thread_ts, user, text, reply_count, replies, reactions, blocks, etc. Next steps (NOT in scope): swap flat file for live slack_sdk.WebClient. Steps: 1) Add slack-sdk dep. 2) Create SlackIngestionClient. 3) Channel iteration + pagination. 4) OAuth token management. 5) Replace file loader with live client behind common interface." \
  --design="1. Research Slack API response schemas: conversations.history, conversations.replies - document exact field names, types, nesting. 2. Create static JSON fixture file (data/slack_fixture.json) matching Slack API shape exactly. 3. Restructure messages.py to load from fixture. 4. Update ContextWindow builder and ingestion layer to consume Slack-shaped data. 5. Ensure downstream pipeline stages still work. 6. Document Slack API fields and next steps for live connection in docstrings." \
  --acceptance="1. Static JSON fixture matches Slack conversations.history + conversations.replies response schema exactly. 2. messages.py loads from the fixture file. 3. All existing pipeline tests pass with restructured data. 4. Docstring documents Slack API fields and next steps for live connection. 5. No Slack SDK client code written - only fixture and loader. 6. All 7 quality gates pass." \
  --silent)
echo "    Slack Fixture:      $SLACK_FIXTURE"

# ─── DOCUMENTATION UPDATE ───────────────────────────────────────────────────
DOCS_UPDATE=$(bd create \
  --title="Update README.md and docs/*.rst to reflect current repo state" \
  --type=task \
  --priority=3 \
  --description="Deep-review the current state of the codebase - architecture, implemented layers, models, pipelines, quality gates, dependencies - and update README.md and all docs/*.rst files to accurately reflect what exists now. Documentation has drifted from implementation: features have been added (instructor structured output, async pipeline, Neo4j backbone, composite scoring) that aren't reflected in docs. The README should serve as an accurate entry point for evaluators and future contributors." \
  --design="1. Read every module under src/evercurrent/ to inventory implemented features. 2. Cross-reference against existing README.md and docs/*.rst for gaps/stale content. 3. Update README.md: project overview, architecture diagram (text), quickstart, environment setup, quality gates, layer-by-layer status. 4. Update docs/*.rst: ensure design-document.rst, any API docs, and architecture docs match reality. 5. Remove references to unimplemented features; add references to implemented ones (instructor, async, Neo4j, scoring calibration, etc.)." \
  --acceptance="1. README.md accurately describes current architecture and all implemented layers. 2. All docs/*.rst files reflect current implementation state. 3. No references to unimplemented features without clear 'planned' markers. 4. Setup/quickstart instructions actually work. 5. All 7 quality gates pass." \
  --silent)
echo "    Docs Update:        $DOCS_UPDATE"

# ─── SPHINX MATERIAL THEME ──────────────────────────────────────────────────
SPHINX_THEME=$(bd create \
  --title="Switch Sphinx docs theme to Material (sphinx-immaterial)" \
  --type=task \
  --priority=3 \
  --description="Change the Sphinx documentation theme from the current default to a Material Design theme. Use sphinx-immaterial (or furo as fallback) for a modern, responsive, searchable documentation site. Update conf.py, add the theme to pyproject.toml dev dependencies, and verify all existing .rst files render correctly under the new theme." \
  --design="1. Add sphinx-immaterial to pyproject.toml dev dependencies. 2. Update docs/conf.py: set html_theme = 'sphinx_immaterial' and configure theme options (palette, font, repo_url, navigation). 3. Build docs locally to verify all .rst files render correctly. 4. Fix any theme-specific markup issues (admonitions, tables, code blocks). 5. Update Makefile docs target if needed." \
  --acceptance="1. sphinx-immaterial added to pyproject.toml dev dependencies. 2. docs/conf.py uses Material theme. 3. All existing .rst files render correctly. 4. Docs build without warnings. 5. All 7 quality gates pass." \
  --silent)
echo "    Sphinx Theme:       $SPHINX_THEME"

# ─── HYBRID SEMANTIC + KEYWORD CONTINUATION DETECTION ────────────────────────
HYBRID_CONTINUATIONS=$(bd create \
  --title="Implement hybrid semantic + keyword continuation detection" \
  --type=feature \
  --priority=1 \
  --description="Replace regex-only continuation detection with hybrid semantic + keyword approach. Current continuations.py uses only regex patterns (@-mentions, quote blocks, back-references). Need to: (1) Add sentence-transformers embedding capability via Embedder protocol, (2) Implement hybrid scoring: regex as fast-path (confidence=1.0), embedding cosine similarity as fallback (threshold ~0.45), (3) Wire detect_continuations() into pipeline.py (currently not called at all), (4) Add ContinuationMatch.confidence field, (5) Pre-compute thread embeddings for efficiency, (6) Add config to pipeline.yml for similarity_threshold and embedding_model. Files to change: continuations.py, pipeline.py, pyproject.toml, pipeline.yml. New file: ingestion/embeddings.py." \
  --design="1. Create Embedder protocol in ingestion/embeddings.py with embed(texts) -> ndarray. 2. Implement SentenceTransformerEmbedder wrapping all-MiniLM-L6-v2. 3. Refactor detect_continuations() to accept optional Embedder param. 4. Keep existing regex checks as fast-path (confidence=1.0). 5. Add semantic similarity fallback: pre-compute thread embeddings once, compute cosine similarity for unmatched standalones, link if above threshold. 6. Add confidence field to ContinuationMatch. 7. Wire into pipeline.py (extract standalones, call detect_continuations, merge results back into bundles). 8. Add continuation config to pipeline.yml. 9. Update tests with mock embedder." \
  --acceptance="1. Existing regex tests still pass. 2. New semantic similarity tests pass with mock embedder. 3. detect_continuations() wired into pipeline.py. 4. Standalones extracted correctly from messages. 5. Continuations merged back into ThreadBundles before context windowing. 6. Config loads similarity_threshold from pipeline.yml. 7. All quality gates pass." \
  --silent)
echo "    Hybrid Continuations: $HYBRID_CONTINUATIONS"

# ─── CENTRALIZE LLM MODEL CONFIG ──────────────────────────────────────────────
CENTRALIZE_MODEL=$(bd create \
  --title="Centralize LLM model config: single pipeline.yml setting propagates to all extraction calls" \
  --type=task \
  --priority=2 \
  --description="Currently the model name is read from pipeline.yml in runner.py at module level, but other places (validation, digest assembly) may instantiate their own model references. Ensure there is ONE canonical model setting in pipeline.yml that propagates to every LLM call in the pipeline - Stage 1 coarse, Stage 2 enrichment, validation, and digest generation. No hardcoded model strings anywhere in source code." \
  --design="1. Audit all files that reference a model name string or read from config independently. 2. Ensure every LLM call site reads model from the single pipeline.yml 'model' key. 3. Remove any hardcoded model strings. 4. Verify with grep that no model string literals remain in src/." \
  --acceptance="1. Changing pipeline.yml model value changes the model used in ALL LLM calls. 2. No hardcoded model strings in src/. 3. All existing tests pass. 4. All quality gates pass." \
  --silent)
echo "    Centralize Model:     $CENTRALIZE_MODEL"

# ─── DOCKER COMPOSE + PERSISTENT STORAGE PIPELINE ─────────────────────────────

DOCKER_COMPOSE=$(bd create \
  --title="Docker Compose: serve-all via docker, Neo4j persistent volume, port forwarding" \
  --type=task \
  --priority=1 \
  --description="Update make serve-all to run docker compose up instead of spawning processes directly. Create docker-compose.yml with services for FastAPI backend, React frontend, and Neo4j. Port forward so app accessible at localhost:5173 (frontend) and localhost:8000 (backend). Add named volume for Neo4j data persistence across container restarts." \
  --design="1. Create docker-compose.yml with 3 services: backend, frontend, neo4j. 2. Frontend on 5173, backend on 8000, Neo4j bolt on 7687/browser on 7474. 3. Named volume for Neo4j data. 4. Update Makefile serve-all to docker compose up. 5. Add Dockerfiles. 6. Pass ANTHROPIC_API_KEY via environment." \
  --acceptance="1. make serve-all starts all services via docker compose. 2. App accessible at localhost:5173. 3. Neo4j data persists across down/up cycles. 4. ANTHROPIC_API_KEY propagates to backend." \
  --silent)
echo "    Docker Compose:       $DOCKER_COMPOSE"

NEO4J_WRITE=$(bd create \
  --title="Write pipeline extraction results to Neo4j via graph/client.py" \
  --type=feature \
  --priority=1 \
  --description="Wire graph/client.py into the pipeline to persist extracted atoms to Neo4j after extraction/validation/filtering. Enables graph-based queries instead of in-memory atom store." \
  --design="1. After confidence_filter, call graph client to write atoms. 2. Store atom properties as nodes, source as relationships. 3. Both sync/async paths write to Neo4j. 4. Graceful degradation if Neo4j unreachable." \
  --acceptance="1. Pipeline writes atoms to Neo4j. 2. Atoms queryable in Neo4j browser. 3. Pipeline doesn't crash if Neo4j unreachable. 4. All tests pass." \
  --silent)
echo "    Neo4j Write:          $NEO4J_WRITE"
bd dep add "$NEO4J_WRITE" "$DOCKER_COMPOSE"

NEO4J_DEDUP=$(bd create \
  --title="Neo4j dedup: skip messages/threads already processed in pipeline" \
  --type=feature \
  --priority=2 \
  --description="Check Neo4j before processing and skip threads that already have extracted atoms. Prevents duplicate LLM calls and duplicate atoms on re-runs." \
  --design="1. Query Neo4j for existing thread_ts before context windowing. 2. Filter out already-processed ThreadBundles. 3. Log skipped vs processed counts. 4. Add threads_skipped to PipelineResult stats." \
  --acceptance="1. Re-run doesn't reprocess extracted threads. 2. New threads processed normally. 3. Stats show skip count. 4. All tests/gates pass." \
  --silent)
echo "    Neo4j Dedup:          $NEO4J_DEDUP"
bd dep add "$NEO4J_DEDUP" "$NEO4J_WRITE"

FAISS_STORE=$(bd create \
  --title="FAISS vectorstore: persist thread/atom embeddings across pipeline runs" \
  --type=feature \
  --priority=1 \
  --description="Add persistent FAISS vectorstore for embeddings. Store to disk, load on startup, mount as Docker volume. Eliminates recomputation across runs." \
  --design="1. Create vectorstore.py with FAISS index wrapper. 2. Save/load from configurable path. 3. Text hash → embedding mapping. 4. Integrate with Embedder protocol. 5. Add faiss-cpu to optional deps. 6. Docker volume mount." \
  --acceptance="1. Embeddings persist to disk. 2. Loaded on next run. 3. Docker volume keeps data. 4. All tests/gates pass." \
  --silent)
echo "    FAISS Store:          $FAISS_STORE"
bd dep add "$FAISS_STORE" "$DOCKER_COMPOSE"

FAISS_DEDUP=$(bd create \
  --title="FAISS dedup: skip atoms/messages that already have stored embeddings" \
  --type=feature \
  --priority=2 \
  --description="Check FAISS before computing embeddings, skip texts with existing vectors. Only embed new/unseen texts, store results. Eliminates redundant embedding computation on re-runs." \
  --design="1. Check FAISS for existing embeddings before model.encode(). 2. Only compute for new texts. 3. Store new embeddings after computing. 4. Log cache hit/miss. 5. Add embeddings_cached/computed stats." \
  --acceptance="1. Re-run doesn't recompute existing embeddings. 2. New texts embedded normally. 3. Stats show cache counts. 4. All tests/gates pass." \
  --silent)
echo "    FAISS Dedup:          $FAISS_DEDUP"
bd dep add "$FAISS_DEDUP" "$FAISS_STORE"

# ─── E2E SMOKE TEST SCRIPT ────────────────────────────────────────────────────
SMOKE_TEST=$(bd create \
  --title="E2E smoke test script: 3 random windows through full pipeline with FAISS + Neo4j" \
  --type=task \
  --priority=1 \
  --description="Create scripts/smoke-test.sh that runs the full pipeline end-to-end on 3 randomly selected context windows. Must exercise: semantic continuation detection (SentenceTransformerEmbedder), FAISS vectorstore caching (CachedEmbedder + VectorStore), LLM extraction (2-stage coarse + enrichment), validation, confidence filtering, and Neo4j persistence. Requires ANTHROPIC_API_KEY and Neo4j running." \
  --design="1. Python script invoked by bash wrapper. 2. Load messages, group threads, select 3 random windows. 3. SentenceTransformerEmbedder wrapped with CachedEmbedder + VectorStore. 4. Run continuation detection, extraction, validation, filter, persist to Neo4j. 5. Save vectorstore. 6. Query Neo4j to verify. 7. Print summary. 8. Exit 0 on success." \
  --acceptance="1. scripts/smoke-test.sh exits 0 on success. 2. Atoms in Neo4j after run. 3. FAISS vectorstore on disk. 4. Re-run uses cached embeddings. 5. Clear error if API key missing or Neo4j down." \
  --silent)
echo "    Smoke Test:           $SMOKE_TEST"

# ─── FRONTEND: DIGEST FROM NEO4J ──────────────────────────────────────────────
DIGEST_NEO4J=$(bd create \
  --title="Frontend: pull digest data from Neo4j via backend API instead of in-memory store" \
  --type=feature \
  --priority=1 \
  --description="Update /digest/{persona_id} endpoint to query atoms from Neo4j first, falling back to in-memory store. Frontend already calls GET /digest/{persona_id} - only backend needs changes. Enables digest across server restarts without re-running pipeline." \
  --design="1. In get_digest(), query Neo4j for atoms via GraphClient. 2. Use Neo4j atoms for scoring if available. 3. Fall back to _atom_store if Neo4j fails or empty. 4. May need new GraphClient method to return full Atom objects. 5. Frontend needs no changes." \
  --acceptance="1. GET /digest returns Neo4j atoms when available. 2. Works without /pipeline/run if Neo4j has data. 3. Graceful fallback if Neo4j down. 4. Frontend displays correctly. 5. All tests pass." \
  --silent)
echo "    Digest from Neo4j:    $DIGEST_NEO4J"

# ─── MESSAGE BATCHES API ──────────────────────────────────────────────────────
BATCH_API=$(bd create \
  --title="Use Anthropic Message Batches API for extraction and validation LLM calls" \
  --type=feature \
  --priority=1 \
  --description="Replace per-window individual LLM calls with Anthropic Message Batches API. Submit all Stage 1, Stage 2, and validation prompts as batches. 50% cost savings, no rate limiting, higher throughput for full 116-window runs." \
  --design="1. Batch client wrapper in llm/batch.py. 2. Collect all prompts per stage, submit as batch. 3. Poll with exponential backoff. 4. Parse results with instructor response_model. 5. Fallback to individual calls if batch unavailable. 6. Track batch vs individual call stats." \
  --acceptance="1. Pipeline uses batch API for all LLM calls. 2. No rate limiting on full run. 3. 50% cost reduction. 4. Graceful fallback. 5. All tests/gates pass." \
  --silent)
echo "    Batch API:            $BATCH_API"

# ═══════════════════════════════════════════════════════════════════════════════
# EPIC: V2 AGGRESSIVE PRUNE - MVP WITH WORKING 3-PERSONA PROTOTYPE
# ═══════════════════════════════════════════════════════════════════════════════

echo ""
echo "  V2 Prune Epic:"

V2_EPIC=$(bd create \
  --title="EPIC: V2 Aggressive Prune - MVP with working 3-persona prototype" \
  --type=feature --priority=0 \
  --description="Retrospective on 98 commits reveals scope creep and dead code. Prune to working MVP." \
  --silent)
echo "    Epic:                 $V2_EPIC"

# Layer 0: Prune dead code
V2_PRUNE=$(bd create \
  --title="Remove OpenAI/Google LLM adapters, instructor dependency, and sync code paths" \
  --type=task --priority=0 \
  --description="Delete llm/openai.py, llm/google.py, sync ExtractionRunner, sync DigestGenerator, sync run_pipeline, legacy ExtractionResponse. Remove instructor. ~1000 LOC of dead code." \
  --silent)
echo "    Prune dead code:      $V2_PRUNE"
bd dep add "$V2_PRUNE" "$V2_EPIC"

# Layer 1: Infrastructure
V2_POSTGRES=$(bd create \
  --title="Add Postgres to docker-compose with SQLAlchemy async ORM models" \
  --type=task --priority=0 \
  --description="Postgres 16 service, SQLAlchemy async models for message/bundle/membership/atom with JSONB, alembic migrations, asyncpg driver." \
  --silent)
echo "    Postgres:             $V2_POSTGRES"
bd dep add "$V2_POSTGRES" "$V2_PRUNE"

V2_INSTRUCTOR=$(bd create \
  --title="Replace instructor with tool_use everywhere, remove instructor dependency" \
  --type=task --priority=1 \
  --description="Remove instructor from anthropic.py, validation.py, generation/runner.py. Replace with direct tool_use calls." \
  --silent)
echo "    Remove instructor:    $V2_INSTRUCTOR"
bd dep add "$V2_INSTRUCTOR" "$V2_PRUNE"

V2_PROMPTS=$(bd create \
  --title="Move all prompts from Python strings to prompts.yml config file" \
  --type=task --priority=1 \
  --description="All extraction/validation/generation prompts and tool schemas to config/prompts.yml. Zero hardcoded prompt strings." \
  --silent)
echo "    Prompts to YAML:      $V2_PROMPTS"
bd dep add "$V2_PROMPTS" "$V2_PRUNE"

# Layer 2: Pipeline features
V2_DELTA=$(bd create \
  --title="Delta pipeline: persist bundles/atoms to Postgres, skip unchanged bundles" \
  --type=task --priority=0 \
  --description="Store ThreadBundles and atoms in Postgres. On re-run, skip unchanged bundles. No kill-and-fill, only delta." \
  --silent)
echo "    Delta pipeline:       $V2_DELTA"
bd dep add "$V2_DELTA" "$V2_POSTGRES"

V2_FAISS=$(bd create \
  --title="FAISS cosine similarity via IndexFlatIP, replace pure-Python implementation" \
  --type=task --priority=1 \
  --description="Use FAISS IndexFlatIP with normalized vectors for cosine similarity. Replace pure-Python cosine_similarity()." \
  --silent)
echo "    FAISS cosine:         $V2_FAISS"
bd dep add "$V2_FAISS" "$V2_PRUNE"

V2_RATELIMIT=$(bd create \
  --title="Batch API rate limit safeguards: respect 1K RPM and 450K input tokens/min" \
  --type=task --priority=1 \
  --description="Token estimation, auto-splitting large batches, exponential backoff on 429. Full 116-window run without rate limits." \
  --silent)
echo "    Rate limits:          $V2_RATELIMIT"
bd dep add "$V2_RATELIMIT" "$V2_PRUNE"

# Layer 3: Frontend
V2_FRONTEND=$(bd create \
  --title="Frontend: rewrite for async batch pipeline with polling progress UI" \
  --type=task --priority=1 \
  --description="POST returns immediately, poll /pipeline/status with real progress bar, stage labels, auto-refresh on complete." \
  --silent)
echo "    Frontend rewrite:     $V2_FRONTEND"
bd dep add "$V2_FRONTEND" "$V2_DELTA"

V2_FE_NEO4J=$(bd create \
  --title="Frontend: load atoms/personas from Neo4j at startup, searchable by person" \
  --type=task --priority=1 \
  --description="Load existing atoms on mount, instant persona switch from cache, search/filter by person." \
  --silent)
echo "    Frontend Neo4j:       $V2_FE_NEO4J"
bd dep add "$V2_FE_NEO4J" "$V2_FRONTEND"

# Layer 4: Polish
V2_BATCHLOG=$(bd create \
  --title="Store LLM batch request/response JSON in Postgres JSONB table" \
  --type=task --priority=2 \
  --description="llm_batch_log table with batch_id, stage, request/response JSONB for auditability and debugging." \
  --silent)
echo "    Batch logging:        $V2_BATCHLOG"
bd dep add "$V2_BATCHLOG" "$V2_POSTGRES"

V2_DOCS=$(bd create \
  --title="Update design-document.rst for V2 simplified architecture" \
  --type=task --priority=2 \
  --description="Rewrite for V2: Anthropic-only, batch API, tool_use, Postgres+Neo4j+FAISS, async-only. Deferred features to Next Steps." \
  --silent)
echo "    Design docs:          $V2_DOCS"
bd dep add "$V2_DOCS" "$V2_DELTA"

V2_TESTS=$(bd create \
  --title="Replace 90% unit test coverage target with 80% + integration tests" \
  --type=task --priority=2 \
  --description="Lower threshold to 80%. Add integration tests: batch API smoke, Postgres round-trip, Neo4j round-trip, FAISS persist, full pipeline e2e." \
  --silent)
echo "    Integration tests:    $V2_TESTS"
bd dep add "$V2_TESTS" "$V2_DELTA"

# ─── PRESENTATION GUIDE ───────────────────────────────────────────────────────
PRESENTATION=$(bd create \
  --title="Create 30-minute deep dive presentation guide (docs/presentation-guide.rst)" \
  --type=task --priority=0 \
  --description="Polished .rst guide for 30-min live deep dive with EverCurrent. Technically rigorous yet approachable. 7 sections: Problem, Architecture, Extraction Pipeline, Scoring Engine, Live Demo, Lessons Learned, Connection to EverCurrent." \
  --silent)
echo "    Presentation Guide:   $PRESENTATION"

VISUAL_PRES=$(bd create \
  --title="Create visual presentation .rst for live 30-min session with Ye Wang" \
  --type=task --priority=0 \
  --description="The 'deck' shown during the call. Sphinx-rendered with architecture SVG, real data examples, tool_use schemas, persona comparisons, V1→V2 story, EverCurrent mapping. Complements the speaker notes in presentation-guide.rst." \
  --silent)
echo "    Visual Presentation:  $VISUAL_PRES"

# ─── DEMO DATASET ──────────────────────────────────────────────────────────────
DEMO_DATASET=$(bd create \
  --title="Create small demo dataset: 1 day of info-dense messages for live demo" \
  --type=task --priority=0 \
  --description="~15-20 messages across 3-4 threads targeting Maya/Elena/Ryan. Async extraction <30s. Pipeline config to switch demo/full dataset." \
  --silent)
echo "    Demo Dataset:         $DEMO_DATASET"
bd dep add "$DEMO_DATASET" "$V2_DOCS"
bd dep add "$VISUAL_PRES" "$DEMO_DATASET"
bd dep add "$PRESENTATION" "$DEMO_DATASET"

# ─── NEXT STEPS ROADMAP ───────────────────────────────────────────────────────
NEXT_STEPS=$(bd create \
  --title="Update next-steps.rst: prototype → production roadmap prioritized by user value" \
  --type=task --priority=1 \
  --description="Rewrite next-steps.rst for V2. Prioritize by user value: live Slack, feedback loop, scheduled runs, multi-team, evaluation. Each item: value + approach + effort." \
  --silent)
echo "    Next Steps:           $NEXT_STEPS"
bd dep add "$NEXT_STEPS" "$V2_DOCS"
bd dep add "$VISUAL_PRES" "$NEXT_STEPS"
bd dep add "$PRESENTATION" "$NEXT_STEPS"

# ─── DESIGN DOC CONSOLIDATION ───────────────────────────────────────────────
DESIGN_CONSOLIDATE=$(bd create \
  --title="Consolidate design-document.rst: V2-only, concise, SVG-rich" \
  --type=task --priority=1 \
  --description="Rewrite design doc for evaluator: remove ALL V1 references, cut ~40-50% length, generate 3+ new SVGs (extraction pipeline, scoring dimensions, data flow, persona model). Eliminate Section 13 (merge into relevant sections). Merge Sections 11+14 into single Production Path. Tighten ADRs to 3-4 sentences each." \
  --acceptance="1. No V1 references. 2. Line count reduced ~40-50%. 3. 3+ new SVGs. 4. Section 13 eliminated. 5. Sections 11+14 merged. 6. Sphinx renders clean. 7. Tests pass." \
  --silent)
echo "    Design Consolidate:   $DESIGN_CONSOLIDATE"
bd dep add "$DESIGN_CONSOLIDATE" "$V2_DOCS"
bd dep add "$VISUAL_PRES" "$DESIGN_CONSOLIDATE"
bd dep add "$PRESENTATION" "$DESIGN_CONSOLIDATE"

# ─── RENAME VERIFICATION ────────────────────────────────────────────────────
RENAME_VERIFY=$(bd create \
  --title="Verify and complete rename: src/evercurrent → src/digest" \
  --type=task --priority=0 \
  --description="User renamed src/evercurrent to src/digest. Verify refactor: update ALL references (imports, pyproject.toml, Makefile, Dockerfile, docker-compose, tests, docs, scripts, conf.py, alembic, README), regenerate API docs, run tests + quality gates." \
  --acceptance="1. All imports updated. 2. pyproject.toml updated. 3. All config/script/doc refs updated. 4. Sphinx docs regenerated. 5. Tests pass. 6. Quality gates pass. 7. Docker builds." \
  --silent)
echo "    Rename Verify:        $RENAME_VERIFY"

# ─── SVG LAYOUT FIX ───────────────────────────────────────────────────────────
SVG_CENTER=$(bd create \
  --title="Center Persistence layer boxes in data-flow.svg" \
  --type=task --priority=2 \
  --description="The boxes under the Persistence layer in docs/_static/data-flow.svg are not centered in the middle of the image. Update the SVG to center them horizontally." \
  --silent)
echo "    SVG Center Fix:       $SVG_CENTER"

# ─── EXTRACTION PIPELINE SVG CLEANUP ──────────────────────────────────────────
SVG_EXTRACTION=$(bd create \
  --title="Uniform box sizes + color legend in extraction-pipeline.svg" \
  --type=task --priority=2 \
  --description="In docs/_static/extraction-pipeline.svg: 1) Make all boxes the same size for visual consistency. 2) Add a color legend explaining what each box color represents." \
  --silent)
echo "    SVG Extraction Fix:   $SVG_EXTRACTION"

# ─── SCORING DIMENSIONS SVG CLEANUP ──────────────────────────────────────────
SVG_SCORING=$(bd create \
  --title="Align input boxes + fix arrowheads in scoring-dimensions.svg" \
  --type=task --priority=2 \
  --description="In docs/_static/scoring-dimensions.svg: 1) Align all input boxes (inputs into the score) in the same row. 2) Ensure every input box is connected to the score box with a visible arrowhead." \
  --silent)
echo "    SVG Scoring Fix:      $SVG_SCORING"

# ─── PERSONA MODEL SVG REDESIGN ──────────────────────────────────────────────
SVG_PERSONA=$(bd create \
  --title="Redesign persona-model.svg as snowflake with Maya Chen centered" \
  --type=task --priority=2 \
  --description="In docs/_static/persona-model.svg: Redesign the diagram as a proper snowflake layout with the 'Maya Chen' box in the center and all related attributes radiating outward from it." \
  --silent)
echo "    SVG Persona Fix:      $SVG_PERSONA"

# ─── SVG COLOR STANDARDIZATION ───────────────────────────────────────────────
SVG_COLORS=$(bd create \
  --title="Standardize SVG box colors: single color or add legend" \
  --type=task --priority=2 \
  --description="Audit all SVGs in docs/_static/*.svg. For diagrams where box color has no semantic meaning, use a single consistent color. For diagrams where color conveys meaning, add a color legend explaining what each color represents." \
  --silent)
echo "    SVG Colors Fix:       $SVG_COLORS"

# ─── PRESENTATION RST UPDATES ────────────────────────────────────────────────
PRES_UPDATE=$(bd create \
  --title="Update presentation.rst: add Assumptions, remove Engineering Maturity & By the Numbers" \
  --type=task --priority=2 \
  --description="In docs/presentation.rst: 1) Add the Assumptions section (from the design doc) after The Problem statement. 2) Delete the 'Engineering Maturity' section. 3) Delete the 'By the Numbers' section." \
  --silent)
echo "    Presentation Update:  $PRES_UPDATE"

# ─── PRESENTATION GUIDE RST UPDATES ──────────────────────────────────────────
PRES_GUIDE_UPDATE=$(bd create \
  --title="Update presentation-guide.rst: add Assumptions, remove sections, align with presentation.rst" \
  --type=task --priority=2 \
  --description="In docs/presentation-guide.rst: 1) Add the Assumptions section after The Problem statement. 2) Delete the 'Engineering Maturity' section. 3) Delete the 'By the Numbers' section. 4) Align the flow with the updated presentation.rst (from evercurrent-u3k). Depends on evercurrent-u3k being completed first." \
  --silent)
echo "    Pres Guide Update:    $PRES_GUIDE_UPDATE"
bd dep add "$PRES_GUIDE_UPDATE" "$PRES_UPDATE"

# ─── DESIGN DOCUMENT UPDATES ─────────────────────────────────────────────────
DESIGN_DOC_UPDATE=$(bd create \
  --title="Design doc updates: reorder 11.7, fix scaling, Slack linking, remove note" \
  --type=task --priority=2 \
  --description="In docs/design-document.rst: 1) Move section 11.7 to the top of section 11. 2) Update Section 8.1 Scaling Characteristics to reflect what was actually built for this prototype. 3) Update the Live Slack Integration section to include a sentence about linking digest items back to source messages (requires live Slack for this). 4) Delete the Design Team note at the top of the document." \
  --silent)
echo "    Design Doc Update:    $DESIGN_DOC_UPDATE"

# ─── OPERATING ASSUMPTIONS AUDIT ─────────────────────────────────────────────
ASSUMPTIONS_AUDIT=$(bd create \
  --title="Audit Operating Assumptions in design doc against codebase reality" \
  --type=task --priority=2 \
  --description="Deep-reason about the entire codebase and verify that the Operating Assumptions section in docs/design-document.rst is entirely reflective of ALL assumptions made for this prototype. Identify any implicit assumptions in the code that are missing from the doc, and flag any documented assumptions that don't match what was actually built." \
  --silent)
echo "    Assumptions Audit:    $ASSUMPTIONS_AUDIT"
bd dep add "$PRES_UPDATE" "$ASSUMPTIONS_AUDIT"

# ─── NEXT-STEPS PLM/ERP ELEVATION ────────────────────────────────────────────
NEXT_STEPS_PLM=$(bd create \
  --title="Elevate PLM/ERP Connectors to Priority 2 in next-steps.rst" \
  --type=task --priority=2 \
  --description="In docs/next-steps.rst: 1) Move 'PLM / ERP Connectors' from the Deferred section up to Priority 2. 2) Expand the description to discuss how a different solution would need to be built to fill in phase context per system/sub-system directly from PLM/ERP, instead of the current approach of inferring from Slack with manual override." \
  --silent)
echo "    Next Steps PLM/ERP:   $NEXT_STEPS_PLM"

# ─── CONCISE PLM/ERP SECTION ─────────────────────────────────────────────────
PLM_CONCISE=$(bd create \
  --title="Make PLM/ERP Connectors section concise in next-steps.rst" \
  --type=task --priority=2 \
  --description="In docs/next-steps.rst: The Priority 2 PLM/ERP Connectors section is too verbose compared to other sections. Make it more concise and consistent in style/length with the other priority sections." \
  --silent)
echo "    PLM Concise:          $PLM_CONCISE"

# ─── SCORING DIMENSIONS ARROWHEAD REMOVAL ─────────────────────────────────────
SVG_NO_ARROWS=$(bd create \
  --title="Remove arrowheads from scoring-dimensions.svg" \
  --type=task --priority=2 \
  --description="In docs/_static/scoring-dimensions.svg: Remove the arrowheads from the connector lines between input boxes and the score box. Keep the lines but without arrow markers." \
  --silent)
echo "    SVG No Arrows:        $SVG_NO_ARROWS"
