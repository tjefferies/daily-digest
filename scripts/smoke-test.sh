#!/usr/bin/env bash
# smoke-test.sh - End-to-end pipeline smoke test
#
# Runs the full pipeline on 3 random context windows:
#   Ingestion → Semantic Continuations (FAISS) → Extraction → Validation → Neo4j
#
# Prerequisites:
#   - ANTHROPIC_API_KEY set in environment
#   - Neo4j running (docker compose up neo4j -d)
#
# Usage:
#   bash scripts/smoke-test.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ── Preflight checks ─────────────────────────────────────────────────────────

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    printf "${RED}ERROR: ANTHROPIC_API_KEY is not set${NC}\n"
    echo "  export ANTHROPIC_API_KEY=sk-ant-..."
    exit 1
fi

printf "${YELLOW}▶ Daily Digest Tool E2E Smoke Test${NC}\n"
printf "  Testing 3 random windows through the full pipeline...\n\n"

# ── Run the Python smoke test ─────────────────────────────────────────────────

PYTHONPATH=src uv run python scripts/smoke_test_runner.py

STATUS=$?
if [ $STATUS -eq 0 ]; then
    printf "\n${GREEN}✓ Smoke test PASSED${NC}\n"
else
    printf "\n${RED}✗ Smoke test FAILED (exit code $STATUS)${NC}\n"
fi
exit $STATUS
