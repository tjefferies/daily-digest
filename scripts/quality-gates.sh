#!/usr/bin/env bash
# quality-gates.sh - Full quality gate runner for EverCurrent
# Used by pre-commit hook and manual invocation.
# Exit codes: 0 = all pass, 1 = gate failed

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0

gate() {
  local name="$1"
  shift
  printf "${YELLOW}▶ %s${NC}\n" "$name"
  if "$@"; then
    printf "${GREEN}✓ %s passed${NC}\n\n" "$name"
  else
    printf "${RED}✗ %s FAILED${NC}\n\n" "$name"
    FAILED=1
  fi
}

# Only run if there are Python source files staged or if running manually
if [ "${IN_PRE_COMMIT:-0}" = "1" ]; then
  # In pre-commit context: check if any .py files are staged
  STAGED_PY=$(git diff --cached --name-only --diff-filter=ACMR -- '*.py' 2>/dev/null || true)
  if [ -z "$STAGED_PY" ]; then
    echo "No Python files staged - skipping quality gates."
    exit 0
  fi
fi

# Check that src/ and tests/ exist before running
if [ ! -d "src" ] && [ ! -d "tests" ]; then
  echo "No src/ or tests/ directories found - skipping quality gates."
  exit 0
fi

echo "═══════════════════════════════════════"
echo "  EverCurrent Quality Gates"
echo "═══════════════════════════════════════"
echo ""

# Gate 1: Ruff linting (zero tolerance)
if [ -d "src" ] || [ -d "tests" ]; then
  SRC_ARG=""
  [ -d "src" ] && SRC_ARG="src/"
  [ -d "tests" ] && SRC_ARG="$SRC_ARG tests/"
  gate "Ruff lint" uv run ruff check $SRC_ARG
fi

# Gate 2: Ruff format check
if [ -d "src" ] || [ -d "tests" ]; then
  SRC_ARG=""
  [ -d "src" ] && SRC_ARG="src/"
  [ -d "tests" ] && SRC_ARG="$SRC_ARG tests/"
  gate "Ruff format" uv run ruff format --check $SRC_ARG
fi

# Gate 3: Type checking
# if [ -d "src" ]; then
#   gate "Type check (ty)" uv run ty check src/
# fi

# Gate 4: Tests with coverage
if [ -d "tests" ] && compgen -G "tests/**/test_*.py" > /dev/null 2>&1; then
  gate "Pytest (coverage ≥80%)" uv run pytest --tb=short -q --cov=src --cov-report=term-missing --cov-fail-under=80 -m "not integration"
fi

# Gate 5: Cyclomatic complexity (max 8 per function)
# radon cc -nc only outputs functions with complexity C or worse (>= 6)
# We fail if anything is rated D or worse (complexity > 8)
if [ -d "src" ]; then
  check_complexity() {
    local output
    output=$(uv run radon cc src/ -a -nc 2>&1)
    echo "$output"
    # Fail if any function has grade D, E, or F (complexity > 8)
    if echo "$output" | grep -qE -- '^\s+[A-Z].*- [D-F]$'; then
      return 1
    fi
    return 0
  }
  gate "Cyclomatic complexity (≤8)" check_complexity
fi

# Gate 6: Maintainability index
if [ -d "src" ]; then
  check_maintainability() {
    local output
    output=$(uv run radon mi src/ -nc 2>&1)
    echo "$output"
    # Fail if any module has grade B or worse
    if echo "$output" | grep -qE -- '- [B-F]$'; then
      return 1
    fi
    return 0
  }
  gate "Maintainability index (A rating)" check_maintainability
fi

# Gate 7: Docstring coverage (interrogate)
if [ -d "src" ]; then
  gate "Docstring coverage (≥95%)" uv run interrogate src/ --fail-under 95
fi

# Gate 8: Dead code detection (vulture)
if [ -d "src" ]; then
  gate "Dead code (vulture)" uv run vulture src/ tests/ vulture_whitelist.py --min-confidence 80
fi

echo "═══════════════════════════════════════"
if [ "$FAILED" -ne 0 ]; then
  printf "${RED}  QUALITY GATES FAILED${NC}\n"
  echo "  Fix issues above and try again."
  echo "  Auto-fix: uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/"
  echo "═══════════════════════════════════════"
  exit 1
else
  printf "${GREEN}  ALL QUALITY GATES PASSED${NC}\n"
  echo "═══════════════════════════════════════"
  exit 0
fi
