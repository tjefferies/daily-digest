.. _presentation:

=====================================================================
Daily Digest Tool 
=====================================================================

*Context-aware information insurance for hardware engineering teams.*

**Travis Jefferies** · Take-Home Deep Dive · April 2026

---------------------------------------------------------------------------
The Problem
---------------------------------------------------------------------------

.. pull-quote::

   A mechanical engineer changes the wall thickness from 2.0mm to 2.5mm
   in a Slack thread on Tuesday. The supply chain lead doesn't see it.
   On Friday, 500 injection-molded parts arrive at the wrong spec.

   **Cost: $40K, 3-week delay, missed DVT milestone.**

This isn't a software problem. In hardware engineering, missed information
is measured in **physical waste and schedule slip** - not in minutes and
keystrokes.

Three things make this hard:

.. list-table::
   :widths: 5 30 65

   * - 1
     - **Relevance is relational**
     - The same spec change is critical to the chassis engineer and
       irrelevant to the firmware developer. You can't score information
       without knowing who's reading it.
   * - 2
     - **Phase context shifts**
     - A DVT tooling issue is irrelevant during Concept and urgent during
       DVT. Phase is per-workstream, not project-wide.
   * - 3
     - **Signals are buried**
     - The spec change happened in ``#chassis-design`` but affects supply
       chain, thermal, and certification. Cross-workstream impact is
       invisible to channel-based consumption.

---------------------------------------------------------------------------
Architecture
---------------------------------------------------------------------------

.. image:: _static/architecture.svg
   :width: 100%

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Principle
     - Implementation
   * - **Anthropic-only**
     - Message Batches API + ``tool_use``. 50% cost savings. No multi-provider abstraction bloat.
   * - **Async-only**
     - FastAPI, SQLAlchemy async, AsyncAnthropic, Neo4j async driver. Zero sync code paths.
   * - **Delta processing**
     - Postgres stores bundles before extraction. Re-run = zero LLM calls on unchanged data.
   * - **Config-driven**
     - All prompts in ``prompts.yml``, all constants in ``pipeline.yml``. Zero hardcoded strings.

---------------------------------------------------------------------------
Data Flow
---------------------------------------------------------------------------

.. image:: _static/data-flow.svg
   :width: 100%

.. code-block:: text

   307 messages → 116 thread bundles → 116 context windows
              → 308 atoms → 5-dim scored → 4-section digests per persona

---------------------------------------------------------------------------
Extraction Pipeline
---------------------------------------------------------------------------

.. image:: _static/extraction-pipeline.svg
   :width: 100%

Two-Stage Extraction
~~~~~~~~~~~~~~~~~~~~~

**Stage 1 - Coarse:** "What happened?" via ``extract_atoms`` tool.

.. code-block:: json

   {
     "type": "DECISION",
     "summary": "Team switching housing material from aluminum to magnesium AZ91D",
     "detail": "FEA confirms 0.6mm wall thickness meets structural requirements...",
     "source": {"channel": "#chassis-design", "thread_ts": "1711990000.000100"}
   }

**Stage 2 - Enrich:** "Who does it affect?" via ``enrich_atom`` tool.

.. code-block:: json

   {
     "workstreams": {"originating": "chassis", "affected": ["supply-chain", "thermal"]},
     "urgency": "high",
     "confidence": 0.92,
     "implicit_decision": false,
     "phase_relevance": ["DVT"]
   }

Validation
~~~~~~~~~~~

``DECISION`` and ``SPEC_CHANGE`` atoms get a second LLM pass. In hardware,
a hallucinated spec value (LLM extracts "3.1 Nm" when the thread said
"2.1 Nm") leads to physical parts manufactured to the wrong tolerance.

All validation requests collected into a **single batch** across all
threads. Invalid atoms: confidence halved → pushed below 0.7 filter.

---------------------------------------------------------------------------
Scoring Engine
---------------------------------------------------------------------------

.. image:: _static/scoring-dimensions.svg
   :width: 100%

.. code-block:: text

   relevance(atom, persona) = 0.30 · workstream + 0.20 · role_type
                             + 0.20 · phase + 0.15 · urgency + 0.15 · social

Same Atom, Different Scores
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The material change decision - "switching housing from aluminum to
magnesium AZ91D" - scores differently for each persona:

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 15 15 15 10

   * - Persona
     - Workstream
     - Role-Type
     - Phase
     - Urgency
     - Social
     - **Total**
   * - **Maya** (ME)
     - 1.00
     - 0.80
     - 1.00
     - 0.75
     - 0.80
     - **0.89**
   * - **Elena** (Supply)
     - 0.70
     - 0.90
     - 0.75
     - 0.75
     - 0.60
     - **0.75**
   * - **Ryan** (EM)
     - 0.80
     - 1.00
     - 1.00
     - 0.75
     - 0.70
     - **0.87**

Maya sees it as "Requires Action" (she owns chassis CAD). Elena sees it
as "Decisions & Changes" (she needs to source Dynacast). Ryan sees it as
schedule risk (8-week vendor lead time vs DVT deadline).

---------------------------------------------------------------------------
Persona Model
---------------------------------------------------------------------------

.. image:: _static/persona-model.svg
   :width: 100%

.. list-table::
   :header-rows: 1
   :widths: 20 25 35 20

   * - Persona
     - Role
     - Top Workstreams
     - Phase Focus
   * - **Maya Chen** (U001)
     - Senior ME
     - chassis (1.0), thermal (0.85)
     - chassis: DVT, thermal: EVT
   * - **Elena Vasquez** (U007)
     - Supply Chain Mgr
     - supply-chain (1.0), chassis (0.5)
     - supply-chain: DVT
   * - **Ryan Torres** (U010)
     - Engineering Mgr
     - chassis (0.8), drivetrain (0.8)
     - chassis: DVT, drivetrain: DVT

The phase vector is **per-workstream, not per-project**. Chassis can be in
DVT while thermal is in late EVT. When the phase toggle shifts thermal
from EVT → DVT, atom rankings change visibly.

---------------------------------------------------------------------------
Live Demo
---------------------------------------------------------------------------

.. admonition:: Switch to browser

   ``http://localhost:5173``

**Demo flow:**

1. **Three personas** - Maya, Elena, Ryan. Same data, different digests.
   Switch between them - **instant** (preloaded from Neo4j cache).

2. **Run the pipeline** - Click "Run Pipeline". Watch the progress bar
   poll ``/pipeline/status`` every 2s with real Anthropic batch counts.

3. **Phase toggle** - Switch thermal from EVT to DVT. Watch atom
   rankings shift. At least 2 items change position.

4. **Neo4j browser** - ``http://localhost:7474``

   .. code-block:: cypher

      MATCH (a:Atom)-[:ORIGINATES_IN]->(w:Workstream)
      RETURN a.summary, w.name LIMIT 10

---------------------------------------------------------------------------
Engineering Maturity
---------------------------------------------------------------------------

**Not just "what I built" - what I built, threw away, and rebuilt better.**

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Built then Deleted
     - Replaced With
   * - OpenAI + Google adapters (420 LOC)
     - Anthropic-only
   * - ``instructor`` middleware
     - Native ``tool_use``
   * - Sync + async dual code paths
     - Async-only
   * - 574 mocked tests (90% coverage)
     - 506 tests + real integration tests
   * - In-memory only, kill-and-fill
     - Postgres delta processing + Neo4j graph

**The big lesson:** 90% coverage with mock-only tests caught zero
production bugs. Every real bug was discovered at runtime: Neo4j
hostname resolution in Docker, Cypher syntax on Neo4j 2025, malformed
UUIDs from the LLM, markdown-fenced JSON. 80% coverage with real
integration tests is worth more.

**The pruning:** Deleted 1,179 lines of dead code in a single commit.
Codebase went from 6,095 LOC to 4,916 LOC while *adding* Postgres,
FAISS, batch API, and delta processing.

---------------------------------------------------------------------------
Mapping to EverCurrent
---------------------------------------------------------------------------

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - This Prototype
     - EverCurrent Product
   * - Thread bundles + semantic continuations
     - Knowledge graph connectivity across 100+ tools
   * - Delta processing (skip unchanged bundles)
     - Change tracking ("what changed in the last 7 days?")
   * - 5-dimension persona scoring
     - Role-aware context for AI coworkers
   * - Two-stage extraction with validation
     - Agentic orchestration with guardrails
   * - Batch API with ``tool_use``
     - LLM integration at manufacturing scale
   * - Cross-workstream ``affected`` tags
     - Breaking knowledge silos across tools

The hardest problem wasn't the LLM pipeline - it was making relevance
*relational*. The same information means different things to different
people depending on their role, their workstreams, and where their project
is in the development lifecycle. **That's the core of what EverCurrent
does.**

---------------------------------------------------------------------------
By the Numbers
---------------------------------------------------------------------------

.. list-table::
   :widths: 30 70

   * - **Commits**
     - 120+
   * - **Issues tracked**
     - 102 (bd/beads issue tracker)
   * - **Source LOC**
     - ~5,500
   * - **Tests**
     - 511 (490 unit + 21 integration)
   * - **Quality gates**
     - 7 (lint, format, coverage, complexity, maintainability, docstrings, dead code)
   * - **Dataset**
     - 307 messages + 18-message demo dataset
   * - **Personas**
     - 3 (Maya, Elena, Ryan)
   * - **LLM**
     - Anthropic Claude Haiku 4.5
   * - **Persistence**
     - Postgres + Neo4j + FAISS
   * - **Infrastructure**
     - Docker Compose (4 services)
