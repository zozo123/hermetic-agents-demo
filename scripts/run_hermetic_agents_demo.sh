#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/hermetic_agents_demo.py" \
  --self-test \
  --out "$ROOT/docs/metrics/hermetic-agents-e2e.json" \
  --transcript "$ROOT/docs/metrics/hermetic-agents-e2e.md" \
  "$@"

echo "Hermetic agents demo wrote:"
echo "  docs/metrics/hermetic-agents-e2e.json"
echo "  docs/metrics/hermetic-agents-e2e.md"
