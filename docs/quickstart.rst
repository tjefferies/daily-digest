Quickstart Guide
================

Prerequisites
-------------

- Python 3.13+ with `uv <https://docs.astral.sh/uv/>`_ package manager
- Docker + Docker Compose
- Node.js 22+ (for frontend development)
- ``ANTHROPIC_API_KEY`` environment variable set

Clone the repository:

.. code-block:: bash

   # SSH
   git clone git@github.com:tjefferies/daily-digest.git
   cd daily-digest

   # Or HTTPS
   git clone https://github.com/tjefferies/daily-digest.git
   cd daily-digest

Set your API key:

.. code-block:: bash

   export ANTHROPIC_API_KEY=sk-ant-...

Docker Compose (Recommended)
-----------------------------

Start all services:

.. code-block:: bash

   make serve-all
   # Or: docker compose up --build

Services:

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Neo4j Browser:** http://localhost:7474
- **Postgres:** localhost:5433

Docker demo mode uses the 18-message demo dataset with async extraction
(``DATASET=demo``, ``EXTRACTION_MODE=async``) for fast ~2 minute pipeline
runs.

Local Development (Without Docker)
-----------------------------------

.. code-block:: bash

   # Install dependencies
   make dev

   # Copy environment config
   cp .env.sample .env
   # Edit .env and set ANTHROPIC_API_KEY

   # Start backend (port 8000)
   make serve

   # Start frontend (port 5173, separate terminal)
   make serve-frontend

   # Run quality gates
   make quality

   # Build docs
   make docs

Makefile Targets
-----------------

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Target
     - Description
   * - ``make dev``
     - Install all dependencies via uv
   * - ``make serve``
     - Start FastAPI backend on port 8000
   * - ``make serve-frontend``
     - Start React frontend on port 5173
   * - ``make serve-all``
     - Docker Compose with all services
   * - ``make quality``
     - Run all 7 quality gates (lint, format, types, tests, complexity, docstrings, dead code)
   * - ``make security``
     - Run security gates (licenses, semgrep, bandit)
   * - ``make docs``
     - Build Sphinx documentation
   * - ``make docs-serve``
     - Build and serve docs with live reload on port 8080
   * - ``make clean``
     - Remove build artifacts

Running the Pipeline
---------------------

.. code-block:: bash

   # Start the pipeline (returns immediately)
   curl -X POST http://localhost:8000/pipeline/run

   # For repeat runs, use ?fresh=true to clear previous data
   curl -X POST "http://localhost:8000/pipeline/run?fresh=true"

   # Poll for progress (every 2 seconds)
   curl http://localhost:8000/pipeline/status

The status response tracks pipeline stages:

.. code-block:: json

   {
     "state": "running",
     "stage": "extraction_stage1",
     "batch_id": "msgbatch_...",
     "progress": {
       "total": 10,
       "succeeded": 6,
       "processing": 4,
       "errored": 0
     },
     "stats": {},
     "error": null
   }

States: ``idle`` to ``running`` to ``complete`` (or ``failed``).
Stages: ``extraction`` to ``extraction_stage1`` to ``extraction_stage2``
to ``validation`` to ``generating_digests`` to ``done``.

Fetching Digests
-----------------

.. code-block:: bash

   # Maya Chen (Mechanical Engineer)
   curl http://localhost:8000/digest/U001

   # Elena Vasquez (Supply Chain Manager)
   curl http://localhost:8000/digest/U007

   # Ryan Torres (Engineering Manager)
   curl http://localhost:8000/digest/U010

   # With phase override
   curl "http://localhost:8000/digest/U001?phase_override=thermal:DVT"

Digests are pre-generated for all 3 personas after pipeline completion.
Persona switching in the frontend is instant (no additional LLM calls).

Batch API vs Async Extraction
------------------------------

The pipeline supports two extraction modes via ``config/pipeline.yml``:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Mode
     - How It Works
     - When to Use
   * - ``batch``
     - Anthropic Message Batches API. Submit all requests, poll for
       results. 50% cost savings. Minimum ~60-120s due to scheduling.
     - Production (cost-optimized)
   * - ``async``
     - Direct ``messages.create()`` calls with ``asyncio.gather()``.
       Concurrent per-window processing. Full price.
     - Live demo (speed-optimized)

Docker Compose defaults to ``async`` for fast demos. The config file
defaults to ``batch`` for cost-efficient production runs.

Configuration
--------------

Settings in ``config/pipeline.yml``:

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Setting
     - Default
     - Description
   * - ``dataset``
     - ``full``
     - ``full`` (307 messages) or ``demo`` (18 messages)
   * - ``extraction_mode``
     - ``batch``
     - ``batch`` (50% savings) or ``async`` (fast)
   * - ``max_concurrency``
     - ``2``
     - Max concurrent async LLM calls
   * - ``confidence_threshold``
     - ``0.7``
     - Minimum confidence for atoms to pass filter
   * - ``model``
     - ``claude-haiku-4-5``
     - Anthropic model for extraction and generation

All settings can be overridden via environment variables:
``DATASET``, ``EXTRACTION_MODE``, ``MAX_CONCURRENCY``.

Troubleshooting
----------------

**Neo4j not ready on startup.** The backend waits 5 seconds before
precooking digests. If Neo4j takes longer, you'll see a warning but the
app still starts. Digests will be generated on-demand instead.

**Pipeline returns empty digests on re-run.** Postgres delta processing
skips previously extracted bundles. Use ``?fresh=true`` on the pipeline
run endpoint, or truncate Postgres tables.

**Missing ANTHROPIC_API_KEY.** The pipeline will fail immediately. Set
the env var before starting services.

**Port 5432 already in use.** Docker maps Postgres to port 5433 to avoid
conflicts with local Postgres installations.

For architecture details, see the :ref:`design-document`.
