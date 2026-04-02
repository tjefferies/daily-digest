:orphan:

.. _presentation-guide:

=====================================================================
30-Minute Presentation Guide
=====================================================================

.. note::

   **Audience:** EverCurrent engineering team (Ye Wang et al.)
   - builders of agentic AI systems for manufacturing.

   **Format:** Live walkthrough with running code. Not slides.

   **Goal:** Show how this take-home maps to what EverCurrent
   actually builds, and demonstrate the thinking behind the tradeoffs.

---------------------------------------------------------------------------
1. The Problem (3 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Start with the failure mode, not the solution. This is the hook that
   makes the rest of the architecture feel inevitable rather than arbitrary.

**Open with this scenario:**

   A mechanical engineer changes the wall thickness from 2.0mm to 2.5mm
   in a Slack thread on Tuesday. The supply chain lead doesn't see it.
   On Friday, 500 injection-molded parts arrive at the wrong spec.
   Cost: $40K, 3-week delay, and a missed DVT milestone.

This isn't a software problem. It's a **hardware engineering** problem where
the cost of missed information is measured in physical waste and schedule slip.

**The core question from the assignment:**

   *How can we provide each team member with a personalized digest based on
   their role and project progress, recognizing that people's focus changes
   over time?*

Three things make this hard:

1. **Relevance is relational, not intrinsic.** The same spec change is
   critical to the chassis engineer and irrelevant to the firmware developer.
   You can't score an atom without knowing who's reading it.

2. **Phase context shifts.** A DVT tooling issue is irrelevant during Concept
   and urgent during DVT. The same person's priorities change as the project
   progresses. Phase is per-workstream, not project-wide.

3. **Important signals are buried.** The spec change happened in
   ``#chassis-design`` but affects supply-chain, thermal, and certification.
   Cross-workstream impact is invisible to channel-based consumption.

.. admonition:: Connection to EverCurrent

   This is exactly the problem EverCurrent solves at scale: fragmented tooling
   creates knowledge silos, and manual coordination doesn't scale. The digest
   tool is a focused instance of EverCurrent's broader "what changed that
   affects me?" question.

---------------------------------------------------------------------------
2. Assumptions (1 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Briefly walk through the operating envelope. These assumptions define
   what was built and - more importantly - what was deliberately scoped out.

Key assumptions (full table in design doc Section 2):

- **A2:** 20–30 people, 300–500 msgs/day. Batch territory, not streaming.
- **A4:** People wear multiple hats. Weighted topic interests, not role buckets.
- **A5:** Phase is per-workstream, not per-project. Linear progression.
- **A9:** English-only text processing.
- **A10:** Message text only - no files, images, or edits tracked.
- **A11:** Validation limited to DECISION and SPEC_CHANGE atoms.
- **A14:** Neo4j failures are soft (digest still works); Postgres is critical.

---------------------------------------------------------------------------
3. Architecture Overview (5 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Pull up the architecture SVG (``docs/_static/architecture.svg``) or
   the running Docker Compose stack. Walk through the data flow left to right.

.. image:: _static/architecture.svg
   :width: 100%

**Data flow:** Slack messages → Thread bundles → Context windows → Atoms → Scored atoms → Personalized digests

**Key architectural decisions:**

- **Anthropic-only with Message Batches API.** 50% cost savings. We tried
  multi-provider (OpenAI, Google) in V1 and ripped it out - added 800 LOC
  of dead abstraction without providing value. Build for one provider first.

- **``tool_use`` for structured output.** The LLM returns clean JSON via
  tool calls. We tried ``instructor`` (a Python middleware library) and
  removed it - the native API does the same thing without a dependency.

- **Three persistence layers:**

  - **Postgres** (SQLAlchemy async) - system of record for messages, bundles,
    atoms, and LLM request/response audit logs. Enables delta processing.
  - **Neo4j** - graph queries for atom→channel→workstream→participant
    relationships. Powers persona-relevant queries.
  - **FAISS** - embedding vector cache with ``IndexFlatIP`` for cosine
    similarity. Prevents recomputing embeddings across pipeline runs.

- **Delta processing, not kill-and-fill.** Postgres stores previously
  extracted bundles. On re-run, only new/changed bundles go to the LLM.
  This is critical when each run costs real money.

.. admonition:: Code path

   ``src/digest/pipeline.py`` → ``_async_run_pipeline_inner()``
   orchestrates the full flow. The pipeline config lives in
   ``config/pipeline.yml`` - all constants (model, thresholds, concurrency)
   are YAML, not hardcoded.

---------------------------------------------------------------------------
4. The Extraction Pipeline (7 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   This is the meatiest section. Walk through the two-stage extraction,
   show the tool schemas, explain why validation matters for hardware.

3.1 Ingestion: Messages → Thread Bundles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

307 synthetic Slack messages across 8 channels, modeled on a real robotics
team (20 engineers, EVT/DVT phases, cross-discipline threads).

**Two-pass thread reconstruction:**

- **Pass 1 (structural):** Group by ``thread_ts``. Simple, fast.
- **Pass 2 (semantic):** Find standalone messages that continue earlier
  threads without using Slack's reply mechanism. Uses a hybrid approach:
  regex fast-path (@-mentions, quote blocks, "re:" back-references) then
  FAISS cosine similarity as a fallback. Confidence scores distinguish
  structural (1.0) from semantic matches.

.. admonition:: Code path

   ``src/digest/ingestion/continuations.py`` → ``detect_continuations()``

3.2 Extraction: Two-Stage Coarse → Enrich
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Why two stages?** A single LLM call that identifies events AND assigns
metadata (workstreams, urgency, confidence, phase relevance) is too much
cognitive load for the model. Splitting into focused stages improves
extraction quality measurably.

- **Stage 1 (Coarse):** "What happened?" → type, summary, detail, source
- **Stage 2 (Enrich):** "How does it affect the team?" → workstreams,
  urgency, confidence, implicit_decision, phase_relevance

Both stages use Anthropic's Message Batches API with ``tool_use`` for
structured output. The tool schemas enforce the exact JSON structure:

.. code-block:: python

   # Stage 1 tool forces the LLM to return atoms in this exact shape
   tools=[{"name": "extract_atoms", "input_schema": {...}}]
   tool_choice={"type": "tool", "name": "extract_atoms"}

   # Stage 2 tool forces enrichment metadata
   tools=[{"name": "enrich_atom", "input_schema": {...}}]
   tool_choice={"type": "tool", "name": "enrich_atom"}

**Batch API advantages:**

- 50% cost savings vs. individual requests
- No per-request rate limiting (1K RPM limit is on batch *operations*)
- Automatic sub-batch splitting for large request lists
- Real-time progress tracking via ``batch.request_counts``

.. admonition:: Code path

   ``src/digest/extraction/batch_runner.py`` → ``BatchExtractionRunner``

3.3 Validation: Why Hardware Needs a Second Pass
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In software, a hallucinated detail is annoying. In hardware, a hallucinated
spec value (LLM extracts "3.1 Nm" when the thread said "2.1 Nm") could
lead to physical parts manufactured to the wrong spec.

``DECISION`` and ``SPEC_CHANGE`` atoms get a second LLM call that re-reads
the source material and checks: did the atom accurately represent what was
said? Invalid atoms have their confidence halved, pushing them below the
filter threshold.

This costs ~30% more in LLM calls for high-risk atoms. Worth it.

.. admonition:: Code path

   ``src/digest/extraction/validation.py`` → ``async_validate_atoms()``
   Rate-limited with configurable semaphore + chunk delay.

3.4 Delta Processing: Don't Re-Extract What Hasn't Changed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every pipeline run checks Postgres for existing bundles:

.. code-block:: python

   processed = await get_processed_bundle_ts(session)
   bundles = [b for b in bundles if b.root_message.message_ts not in processed]

Only new/modified bundles go to the LLM. On the second run with unchanged
data, extraction is **zero LLM calls**. The full request and response bodies
are logged to the ``batch_log`` table for debugging and replay.

---------------------------------------------------------------------------
5. The Scoring Engine (5 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Show the scoring dimensions table. The key insight is that relevance
   is a function of (atom, persona) - the same atom scores differently
   for different readers.

Five dimensions, weighted per persona:

.. list-table::
   :header-rows: 1
   :widths: 25 10 65

   * - Dimension
     - Weight
     - Signal
   * - Workstream proximity
     - 0.30
     - How close is this atom's workstream to the persona's affinities?
   * - Role-type alignment
     - 0.20
     - 5x8 matrix: IC Engineers care about SPEC_CHANGE, Managers care about BLOCKER
   * - Phase alignment
     - 0.20
     - Graduated distance scoring across Concept→EVT→DVT→PVT→MP
   * - Urgency
     - 0.15
     - critical > high > medium > low (uniform 0.25 intervals)
   * - Social signal
     - 0.15
     - Did the persona's collaborators participate in this thread?

**The phase alignment insight:** Phase is per-workstream, not per-project.
Chassis can be in DVT while thermal is still in late EVT. When a persona
toggles their thermal workstream from EVT to DVT, atom rankings shift
visibly - at least 2 items change position. This is testable and tested.

.. admonition:: Code path

   ``src/digest/scoring/composite.py`` → ``score_atoms()``

---------------------------------------------------------------------------
6. Live Demo (5 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Have ``docker compose up`` running. Walk through the frontend.

**Demo flow:**

1. **Show the 3 personas** - Maya (chassis engineer), Elena (supply chain),
   Ryan (engineering manager). Same data, different digests.

2. **Switch personas** - Instant. No loading spinner. All 3 digests are
   precooked at pipeline completion and cached in memory.

3. **Run the pipeline** - Click "Run Pipeline". Show the progress bar
   polling ``/pipeline/status`` every 2 seconds with real batch counts
   from the Anthropic API.

4. **Phase toggle** - Switch thermal from EVT to DVT. Watch atom rankings
   shift. This is Evaluation Criterion 3 from the design doc.

5. **Neo4j browser** - Open http://localhost:7474. Show the
   Atom→Channel→Workstream→Person graph. Run:

   .. code-block:: cypher

      MATCH (a:Atom)-[:ORIGINATES_IN]->(w:Workstream)
      RETURN a.summary, w.name LIMIT 10

---------------------------------------------------------------------------
7. Connection to EverCurrent (2 min)
---------------------------------------------------------------------------

.. admonition:: Speaker Notes

   Close by mapping this solution to their actual product.

This take-home is a focused instance of what EverCurrent builds:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - This Solution
     - Daily Digest Tool Product
   * - Thread bundles + semantic continuations
     - Knowledge graph connectivity
   * - Delta processing (skip unchanged bundles)
     - Change tracking ("what changed in the last 7 days?")
   * - 5-dimension persona scoring
     - Role-aware context for AI coworkers
   * - Two-stage extraction with validation
     - Agentic orchestration with guardrails
   * - Batch API with tool_use
     - LLM integration at manufacturing scale
   * - Cross-workstream affected tags
     - Breaking knowledge silos across 100+ tools

**The hardest problem I solved** wasn't the LLM pipeline - it was making
relevance *relational*. The same information means different things to
different people depending on their role, their workstreams, and where
their project is in the development lifecycle. That's the core of what
EverCurrent does: connecting the right information to the right person
at the right time.

