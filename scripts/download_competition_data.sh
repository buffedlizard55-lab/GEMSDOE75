#!/usr/bin/env bash
# Autonomous competition + public multi-physics data fetch & SHA-256 verification.
# Note: Official DrivenData competition downloads require interactive login at:
#   https://www.drivendata.org/competitions/306/competition-doe-gems/data/
# For automated execution in headless environments, scripts/restore_data.py and
# scripts/fetch_data.py stream SHA-256-pinned mirrors & public USGS/DOE GDR layers
# directly into .cache/ and verify every byte by full 64-hex SHA-256 digest.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

"$PYTHON_BIN" "$ROOT_DIR/scripts/restore_data.py"
"$PYTHON_BIN" "$ROOT_DIR/scripts/fetch_data.py"
