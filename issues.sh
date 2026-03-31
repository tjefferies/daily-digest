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
