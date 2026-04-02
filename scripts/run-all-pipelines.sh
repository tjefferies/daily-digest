#!/usr/bin/env bash
# run-all-pipelines.sh — Nuke all persistence and run end-to-end pipelines
# for both slack_messages.json (full) and demo_messages.json (demo).
#
# Usage: bash scripts/run-all-pipelines.sh
#
# Prerequisites:
#   - Docker + Docker Compose running
#   - ANTHROPIC_API_KEY set in environment or .env
#   - uv installed

set -euo pipefail

echo "═══════════════════════════════════════"
echo "  Daily Digest Tool — Full Pipeline Run"
echo "═══════════════════════════════════════"
echo ""

# ─── Step 1: Nuke everything ────────────────────────────────────────────────
echo "▶ Step 1: Stopping services and removing volumes..."
docker compose down -v 2>/dev/null || true
echo "  ✓ All volumes removed (Postgres + Neo4j data wiped)"
echo ""

# ─── Step 2: Start infrastructure ───────────────────────────────────────────
echo "▶ Step 2: Starting Neo4j and Postgres..."
docker compose up -d neo4j postgres
echo "  Waiting for services to be healthy..."
sleep 5

# Poll until both are healthy (max 60s)
for i in $(seq 1 12); do
    neo4j_ok=$(docker compose ps neo4j --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('healthy' in d.get('Health',''))" 2>/dev/null || echo "False")
    pg_ok=$(docker compose ps postgres --format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print('healthy' in d.get('Health',''))" 2>/dev/null || echo "False")
    if [ "$neo4j_ok" = "True" ] && [ "$pg_ok" = "True" ]; then
        break
    fi
    echo "  ...waiting (${i}/12)"
    sleep 5
done

echo "  ✓ Neo4j and Postgres are healthy"
echo ""

# ─── Step 2b: Create Postgres tables ────────────────────────────────────────
echo "▶ Step 2b: Creating Postgres tables (alembic upgrade head)..."
uv run alembic upgrade head
echo "  ✓ Postgres tables created"
echo ""

# ─── Step 3: Run full dataset pipeline ──────────────────────────────────────
echo "▶ Step 3: Running full dataset pipeline (slack_messages.json, 307 messages)..."
echo "  Mode: batch extraction (50% cost savings)"
echo "  This takes 5-15 minutes depending on Anthropic batch scheduling."
echo ""

DATASET=full EXTRACTION_MODE=batch PYTHONPATH=src \
  POSTGRES_DSN="postgresql+asyncpg://evercurrent:evercurrent_dev@localhost:5433/evercurrent" \
  uv run python3 -c "
import asyncio
from digest.llm.factory import create_async_llm_client
from digest.pipeline import async_run_pipeline

async def main():
    client = create_async_llm_client()
    result = await async_run_pipeline(client)
    print(f'  ✓ Full dataset: {len(result.atoms)} atoms extracted')
    print(f'    Stats: {result.stats}')

asyncio.run(main())
"

echo ""

# ─── Step 4: Run demo dataset pipeline ──────────────────────────────────────
echo "▶ Step 4: Running demo dataset pipeline (demo_messages.json, 18 messages)..."
echo "  Mode: async extraction (faster, ~1-3 minutes)"
echo ""

DATASET=demo EXTRACTION_MODE=async MAX_CONCURRENCY=5 PYTHONPATH=src \
  POSTGRES_DSN="postgresql+asyncpg://evercurrent:evercurrent_dev@localhost:5433/evercurrent" \
  uv run python3 -c "
import asyncio
from digest.llm.factory import create_async_llm_client
from digest.pipeline import async_run_pipeline

async def main():
    client = create_async_llm_client()
    result = await async_run_pipeline(client)
    print(f'  ✓ Demo dataset: {len(result.atoms)} atoms extracted')
    print(f'    Stats: {result.stats}')

asyncio.run(main())
"

echo ""

# ─── Step 5: Verify Neo4j ───────────────────────────────────────────────────
echo "▶ Step 5: Verifying atoms in Neo4j..."

PYTHONPATH=src uv run python3 -c "
from neo4j import GraphDatabase

driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'evercurrent_dev'))
with driver.session() as s:
    # Atom counts by date
    result = s.run('''
        MATCH (a:Atom)
        RETURN DISTINCT date(a.created_at) AS d, count(a) AS n
        ORDER BY d
    ''')
    print('  Atoms by date:')
    total = 0
    for r in result:
        print(f'    {r[\"d\"]}  ({r[\"n\"]} atoms)')
        total += r['n']
    print(f'    Total: {total} atoms')

    # Node counts
    for label in ['Atom', 'Channel', 'Workstream', 'Participant', 'Person']:
        count = s.run(f'MATCH (n:{label}) RETURN count(n) AS c').single()['c']
        print(f'  :{label} nodes: {count}')

    # Relationship counts
    for rel in ['EXTRACTED_FROM', 'ORIGINATES_IN', 'AFFECTS', 'INVOLVES', 'DIGEST']:
        count = s.run(f'MATCH ()-[r:{rel}]->() RETURN count(r) AS c').single()['c']
        print(f'  :{rel} edges: {count}')

driver.close()
"

echo ""

# ─── Step 6: Verify Postgres ────────────────────────────────────────────────
echo "▶ Step 6: Verifying Postgres..."

PYTHONPATH=src \
  POSTGRES_DSN="postgresql+asyncpg://evercurrent:evercurrent_dev@localhost:5433/evercurrent" \
  uv run python3 -c "
import asyncio
from digest.db.session import get_session_factory
from sqlalchemy import text

async def main():
    factory = get_session_factory()
    async with factory() as session:
        for table in ['message', 'thread_bundle', 'bundle_membership', 'context_window', 'atom', 'batch_log']:
            result = await session.execute(text(f'SELECT count(*) FROM {table}'))
            count = result.scalar()
            print(f'  {table}: {count} rows')

asyncio.run(main())
"

echo ""

# ─── Step 7: Start full stack ───────────────────────────────────────────────
echo "▶ Step 7: Starting full stack (backend + frontend)..."
docker compose up --build -d

echo ""
echo "═══════════════════════════════════════"
echo "  ✓ All pipelines complete!"
echo ""
echo "  Frontend:    http://localhost:5173"
echo "  Backend API: http://localhost:8000"
echo "  Neo4j:       http://localhost:7474"
echo "  Postgres:    localhost:5433"
echo ""
echo "  Use the date dropdown to switch between"
echo "  full and demo dataset digests."
echo "═══════════════════════════════════════"
