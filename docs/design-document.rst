.. _design-document:

=====================================================================
Daily Digest Tool: Technical Design Document
=====================================================================

.. note::

   **Design Team**

   This document represents the combined thinking of a cross-functional
   architecture review spanning systems architecture, ML/NLP engineering,
   infrastructure engineering, product engineering, and hardware domain
   engineering.

---------------------------------------------------------------------------
1. Problem Statement
---------------------------------------------------------------------------

1.1 The Core Problem
~~~~~~~~~~~~~~~~~~~~

In hardware engineering, the cost of missed information is measured in weeks,
dollars, and physical waste. A mechanical engineer who misses a tolerance
change on a bracket discovers it when 500 injection-molded parts arrive wrong.
A supply chain lead who misses a component discontinuation notice learns about
it when the production line stops.

The failure mode this system is designed against: **someone changed a spec,
made a decision, or raised a risk in a Slack thread that the affected party
was not watching, and the downstream impact was not caught for days or weeks.**

This is not a summary tool. It is an information insurance policy for teams
where mistakes are physical and often irreversible.

1.2 Why Existing Solutions Fail
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Slack's built-in features are pull-based - they require the user to know what
to look for. Generic AI summarization tools treat all readers as identical.
But a summary of #chassis-design that's useful for the mechanical engineer is
noise for the supply chain lead, who only needs the material change buried in
message 47 of a weight-reduction thread. **Relevance is not a property of a
message; it is a relationship between a message and a reader.**

---------------------------------------------------------------------------
2. Operating Assumptions
---------------------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 8 40 40 12

   * - ID
     - Assumption
     - Architectural Impact
     - Load
   * - A1
     - Cloud LLM access is available (Anthropic API).
     - Pipeline design, cost model, latency.
     - **High**
   * - A2
     - Team size is 20–30 people, 300–500 messages/day across 8–15 channels.
       Nightly batch territory, not streaming.
     - Ingestion architecture, processing budget.
     - **High**
   * - A3
     - Threads are used inconsistently. Some conversations are in-thread,
       others as top-level messages referencing earlier context implicitly.
     - Thread reconstruction logic, context windowing.
     - Medium
   * - A4
     - People wear multiple hats. Relevance must be modeled as weighted topic
       interests per user, not rigid role buckets.
     - Persona model, relevance scoring.
     - **High**
   * - A5
     - Different subsystems are in different phases simultaneously
       (Concept, EVT, DVT, PVT, MP). Phase is a property of a workstream,
       not the project.
     - Phase representation, scoring.
     - **High**
   * - A6
     - No PLM/ERP connectors for the prototype. Phase status is manually
       configured.
     - Context backbone population.
     - Medium
   * - A7
     - The digest is a read-only artifact covering the previous 24 hours.
     - Digest rendering, feedback availability.
     - Low
   * - A8
     - Slack channels are organized primarily by workstream
       (``#chassis-design``, ``#supply-chain``, etc.) with cross-cutting
       channels (``#amr-general``, ``#testing``).
     - Channel-to-workstream mapping.
     - Medium

---------------------------------------------------------------------------
3. System Architecture
---------------------------------------------------------------------------

The system is an async pipeline that transforms raw Slack messages into
persona-specific daily digests. It consists of five layers with defined
responsibility and interface contracts.

.. image:: _static/architecture.svg
   :alt: Daily Digest Toolfive-layer pipeline architecture
   :width: 100%

3.1 Data Flow
~~~~~~~~~~~~~

.. image:: _static/data-flow.svg
   :alt: Data transformation pipeline
   :width: 100%

The pipeline is triggered on demand via ``POST /pipeline/run`` (production:
scheduled daily at 06:00 local time).

**Layer 1 - Ingest.** Messages are loaded, grouped into thread bundles, and
checked for semantic continuations using FAISS cosine similarity (threshold
0.45). Each bundle is assembled into a context window: short threads are
included in full; long threads are compressed to the root message, top-reacted
replies, and final 5 messages.

**Layer 2 - Extract.** Each context window passes through a two-stage
Anthropic Batch API pipeline (see Section 4). Stage 1 extracts coarse atoms;
Stage 2 enriches with metadata. Both use ``tool_use`` for structured output.

**Layer 3 - Validate & Filter.** All ``DECISION`` and ``SPEC_CHANGE`` atoms
are validated in a single batch against their source context. Invalid atoms
have confidence halved. A confidence filter (threshold ≥ 0.7) removes
low-quality atoms.

**Layer 4 - Score.** Each validated atom is scored for each persona across
five relevance dimensions (see Section 5). Atoms are ranked by composite
score, capped at the persona's ``max_items``.

**Layer 5 - Generate.** Scored atoms and persona context are passed to the
LLM, which generates a four-section digest via ``tool_use`` structured output.

3.2 Persistence
~~~~~~~~~~~~~~~

**Postgres** (:5433). BCNF schema: ``message`` → ``bundle_membership`` →
``thread_bundle`` → ``context_window`` → ``atom``. Plus ``batch_log`` for
full LLM request/response JSONB bodies. SQLAlchemy async with asyncpg.

**Neo4j** (:7687). ``:Atom`` → ``:Channel`` / ``:Workstream`` /
``:Participant`` graph. Used for digest precooking on startup and
graph-based queries.

**FAISS.** IndexFlatIP with L2-normalized vectors for cosine similarity.
Persistent embedding cache with sentence-transformers (all-MiniLM-L6-v2).

3.3 Delta Processing
~~~~~~~~~~~~~~~~~~~~

Bundles are persisted to Postgres *before* extraction. On re-run, the pipeline
queries for existing bundles and only extracts new/changed ones. This means
zero LLM calls on unchanged data - critical for cost control during
development and idempotent production runs.

3.4 Tech Stack
~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Layer
     - Technology
     - Rationale
   * - Frontend
     - React + TypeScript + Tailwind CSS
     - Persona switcher, sectioned digest, phase toggle.
   * - Backend
     - Python (FastAPI), Pydantic v2
     - Best LLM library ecosystem, strong typing.
   * - LLM
     - Anthropic (``claude-haiku-4-5``), Message Batches API, ``tool_use``
     - Structured output without dependencies. 50% batch savings.
   * - Persistence
     - Postgres + Neo4j + FAISS
     - Delta processing, graph queries, embedding cache.
   * - Config
     - YAML (``config/pipeline.yml``, ``prompts.yml``, ``personas.yml``,
       ``scoring.yml``, ``phases.yml``)
     - All prompts and constants externalized.
   * - Docs
     - Sphinx (reStructuredText)
     - Professional documentation site.

---------------------------------------------------------------------------
4. Extraction Pipeline (Layer 2)
---------------------------------------------------------------------------

.. image:: _static/extraction-pipeline.svg
   :alt: Two-stage extraction pipeline
   :width: 100%

4.1 Thread Reconstruction
~~~~~~~~~~~~~~~~~~~~~~~~~

Thread reconstruction operates in three passes:

**Pass 1 - Structural grouping.** Group messages by Slack ``thread_ts``.

**Pass 2 - Implicit threading.** Identify top-level messages that continue
earlier conversations using a hybrid approach: structural matching
(@-mentions, quote blocks, back-references) as a fast path, and semantic
embedding cosine similarity (threshold 0.45) as a fallback. Channel-aware,
first-match.

**Pass 3 - Context windowing.** Assemble each conversational unit into a
context window within LLM token limits. Long threads are compressed to the
opener, most-reacted messages, and final 5 messages.

4.2 Information Atom Types
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 18 42 40

   * - Atom Type
     - Definition
     - Example
   * - ``DECISION``
     - A choice constraining future work: material selections, design
       approaches, vendor choices.
     - "Team agreed to switch housing from aluminum to magnesium."
   * - ``SPEC_CHANGE``
     - A modification to an established spec, tolerance, or requirement.
       Highest-risk type - silently invalidates downstream work.
     - "Motor torque updated from 2.5 Nm to 3.1 Nm."
   * - ``ACTION_ITEM``
     - A task assigned to a specific person with an implied deadline.
     - "Sarah will send updated STEP files by Friday."
   * - ``BLOCKER``
     - An impediment preventing progress on a workstream.
     - "Can't proceed with enclosure until thermal provides heat specs."
   * - ``RISK``
     - A concern that could affect schedule, cost, or performance.
     - "Vendor says FPGA lead time may extend to 16 weeks."
   * - ``TEST_RESULT``
     - Outcome of a test or validation activity.
     - "Vibration test on chassis rev C passed all axes."
   * - ``STATUS_UPDATE``
     - Progress report on a workstream or task.
     - "PCB layout is 80% complete, sending to fab Tuesday."
   * - ``QUESTION``
     - An unanswered question requiring input from outside the conversation.
     - "Does IP67 sealing apply to the debug connector?"

4.3 Two-Stage Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~

Extraction uses two stages to reduce cognitive load per LLM call:

- **Stage 1 (Coarse):** Identifies events and returns lightweight atom dicts:
  ``type``, ``summary``, ``detail``, ``source``. Uses the ``extract_atoms``
  tool via Anthropic Batch API.

- **Stage 2 (Enrichment):** For each coarse atom, assigns metadata:
  ``workstreams``, ``urgency``, ``confidence``, ``implicit_decision``,
  ``phase_relevance``. Uses the ``enrich_atom`` tool. Both the coarse atom
  and original thread context are provided.

Both stages use ``tool_use`` for Pydantic-validated structured output, with
the Anthropic Message Batches API for 50% cost savings.

4.4 Prompt Design Principles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Extract conclusions, not discussions.** A 30-message debate should produce a
single ``DECISION`` atom, not a summary of the debate.

**Flag implicit decisions.** When someone casually says "let's just go with
magnesium" and the conversation moves on, that is an implicit decision with
procurement, tooling, and certification consequences. The LLM surfaces these
with a confidence field.

**Identify cross-workstream impacts.** Each atom tags the originating
workstream *and* affected workstreams. A material change in mechanical affects
supply chain. These cross-tags enable surfacing information to people who
weren't in the original conversation.

4.5 Validation and Hallucination Mitigation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In hardware engineering, a hallucinated tolerance value is actively dangerous.
Three safeguards:

**Confidence scoring.** Atoms below threshold (0.7) are excluded.

**Source anchoring.** Every atom links to its Slack thread and message range.
The reader can always verify.

**Extraction validation.** ``SPEC_CHANGE`` and ``DECISION`` atoms undergo a
second LLM pass comparing the extracted atom against its source context.
Failed atoms are demoted (confidence halved, warning appended). All
validation requests across all threads are collected into a single batch.

---------------------------------------------------------------------------
5. Relevance Scoring (Layer 4)
---------------------------------------------------------------------------

.. image:: _static/scoring-dimensions.svg
   :alt: Five-dimension composite scoring model
   :width: 100%

5.1 Core Insight
~~~~~~~~~~~~~~~~

A message is not inherently important. It is important *to someone* in
*some context*. The same ``SPEC_CHANGE`` - "motor torque increased from
2.5 Nm to 3.1 Nm" - is critical for the power systems engineer, important
for supply chain, contextual for the PM, and irrelevant for the enclosure ME.

5.2 Scoring Dimensions
~~~~~~~~~~~~~~~~~~~~~~~

Each atom is scored per persona across five dimensions:

**Workstream Proximity (0.30).** Does this atom originate from or affect a
workstream the persona tracks? Each persona has a weighted affinity vector.
Originating workstream scores 1.0; affected workstreams score 0.7;
affinities scale from there.

**Role-Type Alignment (0.20).** Does this atom type typically matter to this
role archetype? Encoded as a 5×8 role-type affinity matrix:

.. code-block:: text

   Role            DECISION  SPEC_CHG  ACTION  BLOCKER  RISK  TEST  STATUS  QUESTION
   IC Engineer       0.8      1.0       0.7     0.6     0.5   1.0    0.3     0.6
   Eng Manager       1.0      0.7       0.8     1.0     0.9   0.6    0.9     0.5
   Supply Chain      0.7      0.9       0.8     0.7     1.0   0.3    0.5     0.4

**Phase Alignment (0.20).** Graduated distance scoring across the linear
phase order (Concept=0, EVT=1, DVT=2, PVT=3, MP=4). Exact match = 1.0,
adjacent = 0.75, decreasing with distance. Because different workstreams
occupy different phases (assumption A5), lookup is per-workstream.

**Urgency (0.15).** Atom urgency (low=0.25, medium=0.5, high=0.75,
critical=1.0). Boosts relevance but doesn't override it - an urgent
firmware atom is still irrelevant to a mechanical engineer.

**Social Signal (0.15).** Was this atom from a conversation involving the
persona's close collaborators? Proxy for the informal trust network.

5.3 Composite Score
~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   relevance(a, p) = w₁·workstream(a,p) + w₂·role_type(a,p)
                    + w₃·phase(a,p) + w₄·urgency(a) + w₅·social(a,p)

   where Σwᵢ = 1.0 and wᵢ are persona-specific.

Atoms are ranked by composite score. The top *N* (default: 25) form the
digest. Atoms above 0.85 are placed in "Requires Your Action" regardless
of rank position.

---------------------------------------------------------------------------
6. Persona Model (Layer 3)
---------------------------------------------------------------------------

.. image:: _static/persona-model.svg
   :alt: Persona model structure
   :width: 100%

A persona models what a specific person cares about - richer than a role
label, more stable than a per-query signal.

.. code-block:: json

   {
     "user_id": "U001",
     "name": "Maya Chen",
     "role_archetype": "IC Engineer",
     "title": "Senior Mechanical Engineer",
     "workstream_affinities": {
       "chassis": 1.0, "thermal": 0.85, "drivetrain": 0.4,
       "supply-chain": 0.3, "power-systems": 0.2
     },
     "phase_context": {"chassis": "DVT", "thermal": "EVT"},
     "scoring_weights": {
       "workstream_proximity": 0.30, "role_type_alignment": 0.20,
       "phase_alignment": 0.20, "urgency": 0.15, "social_signal": 0.15
     },
     "collaborator_graph": ["U003", "U008", "U013", "U020"],
     "digest_preferences": {
       "max_items": 25, "critical_threshold": 0.85,
       "include_broader_context": true
     }
   }

The phase vector is a first-class entity: a robotics program might have
chassis in DVT, thermal in late EVT, sensors in EVT, and end-effector in
Concept - all simultaneously. Phase alignment scoring queries each
workstream independently.

For the prototype, three personas are manually defined. Production
initialization would draw from Slack metadata (channel membership, message
frequency), organizational data (title, team), and self-declaration.

---------------------------------------------------------------------------
7. Digest Generation (Layer 5)
---------------------------------------------------------------------------

7.1 Digest Structure
~~~~~~~~~~~~~~~~~~~~

Four priority-tiered sections, consistent structure across personas but
different *contents* based on relevance scoring:

**Section 1 - Requires Your Action.** Atoms above the critical threshold
involving an explicit or inferred action. Intentionally short (0–5 items).

**Section 2 - Decisions & Changes.** ``DECISION`` and ``SPEC_CHANGE`` atoms
from relevant workstreams. This catches the "material change you didn't know
about" failure mode.

**Section 3 - Progress & Risks.** ``STATUS_UPDATE``, ``TEST_RESULT``,
``BLOCKER``, and ``RISK`` atoms ordered by relevance.

**Section 4 - Broader Context.** Lower-relevance atoms for general team
awareness. Optional (controlled by persona preference), capped at 5 items.

7.2 Generation Prompt
~~~~~~~~~~~~~~~~~~~~~

The LLM receives the persona definition, scored atoms in priority order, and
a system prompt defining structure, tone, and formatting.

**Tone: Briefing, not newsletter.** Terse, specific, actionable. Hardware
engineers want information density, not narrative flair.

**Format: Scannable.** Each item gets a bold headline, 1–2 sentence context,
and a source link. 30-second scan of headlines, then drill into details.

**Judgment: Do not editorialize.** Report what happened and who is affected.
No opinions, no recommendations. Trust is lost the moment the digest adds
unsolicited commentary.

---------------------------------------------------------------------------
8. Deployment and Cost
---------------------------------------------------------------------------

8.1 Scaling Characteristics
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 15 35 35 15

   * - Tier
     - Profile
     - Architecture
     - Prototype?
   * - Small
     - 10–30 people, 200–500 msgs/day
     - Nightly batch. Postgres. One API key.
     - **Yes**
   * - Medium
     - 50–100 people, 1K–3K msgs/day
     - Parallelized extraction. Redis cache.
     - No
   * - Large
     - 100–500 people, 5K–20K msgs/day
     - Stream processor (Kafka). Searchable atom index. Self-hosted inference.
     - No

8.2 Cost Model (Small Tier)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: text

   Extraction pass:    ~150 units × ~2,000 tokens   = 300K input tokens
   Validation pass:    ~30 high-risk atoms × ~1,500  =  45K input tokens
   Generation pass:    ~25 personas × ~3,000 tokens  =  75K input tokens
   Output tokens:      ~150K across all passes
   ─────────────────────────────────────────────────────────────────
   Daily total:        ~420K input + ~150K output (with 50% batch discount)
   Estimated cost:     ~$3–$8/day ($90–$240/month)

The tool pays for itself if it prevents a single procurement error per
quarter.

8.3 On-Premises Path
~~~~~~~~~~~~~~~~~~~~

For teams where data sensitivity prohibits cloud LLM access (ITAR, trade
secrets), the ``AsyncLLMClient`` protocol supports self-hosted inference
via vLLM or TGI with open-weight models. Higher infra cost, lower extraction
quality, but all data stays within the network boundary.

---------------------------------------------------------------------------
9. Prototype Scope
---------------------------------------------------------------------------

9.1 What the Prototype Demonstrates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A **proof of mechanism**: the same stream of Slack messages, processed
through a context-aware pipeline, produces meaningfully different digests
for different personas and project phases.

Includes: synthetic dataset (307 messages, 8 channels, plus an 18-message
demo dataset for fast live demos), working extraction pipeline, five-dimension
relevance scoring, three fully defined personas, and an interactive frontend
with persona switching and phase-transition toggles.

Persistence: Postgres (bundles, atoms, context windows, batch logs), Neo4j
(atom graph), and FAISS (embedding cache). Delta processing ensures re-runs
skip unchanged bundles.

9.2 What the Prototype Does Not Include
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Live Slack integration, user accounts/authentication, the adaptive feedback
loop (Section 5 describes the mechanism; prototype uses static weights),
PLM/ERP connectors, or production observability.

9.3 Synthetic Data Design
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The synthetic dataset exhibits: realistic hardware communication patterns,
deliberate "buried signals" (cross-workstream impacts a naive summary would
miss), phase diversity (some workstreams in EVT, others in DVT), and thread
depth variety (2–3 messages to 30–50 message arcs).

Buried signal examples:

1. A material change ("let's go with magnesium") buried in a weight-reduction
   thread that has procurement implications.
2. A test failure whose root cause implicates a different subsystem.
3. A vendor lead-time update affecting a workstream the supply chain lead
   doesn't directly follow.

---------------------------------------------------------------------------
10. Evaluation Criteria
---------------------------------------------------------------------------

**Differential relevance.** Different personas receive meaningfully different
digests. The ME's digest emphasizes chassis test results; the supply chain
lead's emphasizes material changes and vendor risks; the EM's emphasizes
blockers and cross-functional dependencies.

**Signal surfacing.** The digest surfaces "buried signals" - the material
change should appear in the supply chain lead's digest even though it
originated in #chassis-design.

**Phase sensitivity.** The digest changes when a workstream transitions
between phases. EVT emphasizes design decisions; DVT emphasizes vendor
readiness and validation results.

Production metrics: time-to-awareness (target: same-day), missed-signal rate
(target: zero above critical threshold), engagement rate (target: 70%+),
false positive rate in "Requires Action" (target: <15%).

---------------------------------------------------------------------------
11. Production Path
---------------------------------------------------------------------------

11.1 Live Slack Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Replace the fixture with real Slack API via OAuth bot token. Scopes:
``channels:history``, ``channels:read``, ``users:read``. Implement
incremental ingestion with high-water mark per channel. Handle message edits
and deletes.

11.2 Scheduled Pipeline
~~~~~~~~~~~~~~~~~~~~~~~

Replace the manual "Run Pipeline" button with daily scheduled execution
(cron or Slack webhook trigger). Pre-cook digests for all personas before
the workday starts.

11.3 Adaptive Feedback Loop
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Track implicit signals (dismissals, pins, click-throughs, dwell time) to
adjust per-user scoring weights over time. Exponential moving average with
slow learning rate (α = 0.05). Guardrails: weights cannot deviate more than
±0.15 from defaults.

11.4 Multi-Team Support
~~~~~~~~~~~~~~~~~~~~~~~

Generalize from the 8-channel robotics team to arbitrary Slack workspaces.
Requires dynamic channel discovery, workstream inference, and persona
auto-detection from Slack metadata.

11.5 Evaluation Framework
~~~~~~~~~~~~~~~~~~~~~~~~~

Golden-set annotations with precision/recall metrics. Hallucination rate
tracking. Graded scoring beyond binary valid/invalid.

11.6 Multi-Provider LLM
~~~~~~~~~~~~~~~~~~~~~~~~

The ``AsyncLLMClient`` protocol supports additional adapters (OpenAI, Google,
self-hosted via vLLM). Re-add when a second provider is needed. The protocol
includes provider failover and model evaluation harness capabilities.

11.7 Stakeholder Questions
~~~~~~~~~~~~~~~~~~~~~~~~~~

These questions should be answered before production scoping:

- **IP classification:** Can Slack content be processed by cloud LLM, or is
  on-prem required? This is the highest-impact question.
- **PM tool integration:** Does the team use Jira/Linear for phase tracking?
  Automated phase detection eliminates manual toggles.
- **Multi-source ingestion:** Do decisions also occur in email, Google Docs,
  CAD comments, or PLM systems?
- **User research:** Concrete "I missed X and it cost us Y" stories are the
  most valuable input for tuning extraction and scoring.

---------------------------------------------------------------------------
12. Architecture Decision Records
---------------------------------------------------------------------------

**ADR-001: Batch over stream.** The target scale (300–500 msgs/day) does
not justify streaming infrastructure. Batch processing with a daily job
covers the use case. Truly urgent items use Slack's native notifications -
the digest is for *awareness*, not *alerting*.

**ADR-002: LLM extraction over rule-based NLP.** "Let's just go with
magnesium" is trivially identified as a material decision by an LLM but
nearly impossible to catch with rules. Higher per-message cost (~$0.01–$0.03)
but dramatically better recall for implicit decisions. The value of one caught
missed decision vastly exceeds the monthly API cost.

**ADR-003: Atom granularity.** One atom per discrete information unit, not
per message or thread. A 30-message thread might contain a test result, a
decision, and an action item - different personas care about different atoms
from the same thread.

**ADR-004: Phase as vector, not scalar.** Phase is tracked per-workstream
because different subsystems routinely occupy different development phases.
A single project-level phase label produces incorrect relevance scoring for
multi-workstream personas.

**ADR-005: Two-pass validation for high-risk atoms.** ``SPEC_CHANGE`` and
``DECISION`` atoms undergo a second LLM pass checking for overstated
conclusions and fabricated details. ~30% increase in extraction cost,
justified by the cost of hallucinated spec values in hardware.
