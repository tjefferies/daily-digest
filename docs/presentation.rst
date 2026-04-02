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

   **Cost: $40K, 3-week delay, missed Design Validation Test (DVT) milestone.**

This isn't a software problem. In hardware engineering, missed information
is measured in **physical waste and schedule slip**, not in minutes and
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
Assumptions
---------------------------------------------------------------------------

The prototype is designed for a small robotics hardware company and makes many simplifying assumptions:

.. list-table::
   :header-rows: 1
   :widths: 8 60 32

   * - ID
     - Assumption
     - Impact
   * - A1
     - Cloud LLM access available (Anthropic API).
     - **High**: pipeline design, cost model
   * - A2
     - 20 to 30 people, 300 to 500 messages/day across 8 to 15 channels. Nightly batch, not streaming.
     - **High**: ingestion architecture
   * - A3
     - Threads used inconsistently; some conversations span top-level messages implicitly.
     - Medium: thread reconstruction logic
   * - A4
     - People wear multiple hats. Relevance is weighted topic affinities per user, not rigid roles.
     - **High**: persona model, scoring
   * - A5
     - Different workstreams in different phases simultaneously (Concept,
       Engineering Validation Test (EVT), DVT, Production Validation Test
       (PVT), Mass Production (MP)).
     - **High**: phase representation
   * - A6
     - No Product Lifecycle Management (PLM) / Enterprise Resource Planning (ERP) connectors. Phase status is manually configured.
     - Medium: context backbone
   * - A7
     - Digest is read-only. Prototype processes all messages; production filters to prior 24h.
     - Low: temporal scope
   * - A8
     - Channels organized by workstream (``#chassis-design``, ``#supply-chain``) plus cross-cutting channels.
     - Medium: channel mapping
   * - A9
     - All communication in English. Regex patterns, prompts, and taxonomy are English-only.
     - Medium: multilingual path requires rewrite
   * - A10
     - Actionable information is in message text only. Files, images, edits, deletions not processed.
     - Medium: ingestion scope
   * - A11
     - Validation targets only ``DECISION`` and ``SPEC_CHANGE``. Other types pass through on confidence alone.
     - Medium: validation cost model
   * - A12
     - Phase progression is linear (Concept to EVT to DVT to PVT to MP). Rollbacks not modeled.
     - Medium: phase scoring
   * - A13
     - All timestamps UTC. No timezone configuration.
     - Low
   * - A14
     - Neo4j failures are non-critical (soft fail). Postgres failures abort the pipeline.
     - Medium: fault tolerance hierarchy

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

   307 messages -> 116 thread bundles -> 116 context windows
              -> 308 atoms -> 5-dim scored -> 4-section digests per persona

---------------------------------------------------------------------------
Extraction Pipeline
---------------------------------------------------------------------------

.. image:: _static/extraction-pipeline.svg
   :width: 100%

Two-Stage Extraction
~~~~~~~~~~~~~~~~~~~~~

**Stage 1, Coarse:** "What happened?" via ``extract_atoms`` tool.

.. code-block:: json

   {
     "type": "DECISION",
     "summary": "Team switching housing material from aluminum to magnesium AZ91D",
     "detail": "FEA confirms 0.6mm wall thickness meets structural requirements...",
     "source": {"channel": "#chassis-design", "thread_ts": "1711990000.000100"}
   }

**Stage 2, Enrich:** "Who does it affect?" via ``enrich_atom`` tool.

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
threads. Invalid atoms have confidence halved, pushing them below the 0.7
filter.

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

The material change decision, "switching housing from aluminum to
magnesium AZ91D," scores differently for each persona:

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
from EVT to DVT, atom rankings change visibly.

---------------------------------------------------------------------------
Demo
---------------------------------------------------------------------------

Generation Pipeline
~~~~~~~~~~~~~~~~~~~~

.. raw:: html

   <video controls width="100%">
     <source src="_static/pipeline.mov" type="video/quicktime">
     Your browser does not support the video tag.
   </video>

Frontend
~~~~~~~~~~~~~~~~~~~~

1. **Three personas.** Maya, Elena, Ryan. Same data, different digests.
   Switch between them; preloaded from Neo4j cache, so it's instant.

2. **Neo4j browser.** ``http://localhost:7474``

   .. code-block:: cypher

      // Digest model: Person → DigestRun → Atom
      MATCH (p:Person)-[:HAS_DIGEST]->(dr:DigestRun)
            -[r:INCLUDES]->(a:Atom)
      RETURN p.user_id, dr.run_date, a.summary, r.score
      ORDER BY r.score DESC LIMIT 10

      // Atom → Workstream graph
      MATCH (a:Atom)-[:ORIGINATES_IN]->(w:Workstream)
      RETURN a.summary, w.name LIMIT 10

---------------------------------------------------------------------------
Complexity Analysis
---------------------------------------------------------------------------

Pipeline Costs
~~~~~~~~~~~~~~~

**M** = messages, **B** = bundles, **S** = standalone messages,
**W** = context windows, **A** = atoms, **V** = validated atoms
(DECISION + SPEC_CHANGE), **P** = personas.

.. list-table::
   :header-rows: 1
   :widths: 30 25 20 25

   * - Stage
     - Time
     - LLM Calls
     - Bottleneck
   * - Ingestion
     - O(M log M + S x B)
     - 1 (embed)
     - Continuation detection
   * - Extraction (batch)
     - O(W + A)
     - ~5-10
     - Batch API scheduling
   * - Extraction (async)
     - O(W + A)
     - W + A (~450)
     - Per-request rate limits
   * - Validation
     - O(V + A)
     - 1
     - Single batch
   * - Scoring
     - O(P x A log A)
     - 0
     - Per-persona sort
   * - Generation
     - O(P x max_items)
     - P (~3)
     - One LLM call/persona
   * - Neo4j persist
     - O(P x A)
     - 0
     - :DigestRun + :INCLUDES edges

LLM Call Budget
~~~~~~~~~~~~~~~~

.. code-block:: text

   Batch mode (production):   ~10 API calls, 50% batch discount
   Async mode (demo):         ~455 API calls, full price, faster latency

   Memory peak:               ~20-40 MB
   Dominant cost:              LLM API latency, not CPU

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

The hardest problem wasn't the LLM pipeline. It was making relevance
*relational*. The same information means different things to different
people depending on their role, their workstreams, and where their project
is in the development lifecycle. **That's the core of what EverCurrent
does.**