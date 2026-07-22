#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

find_python() {
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)" || {
  echo "Python 3.11 or newer is required. Install python3.11+ and try again." >&2
  exit 1
}

"$PYTHON_BIN" - <<'PY' || {
import ensurepip
import venv
PY
  echo "The selected Python cannot import venv/ensurepip. Install the distribution venv package." >&2
  exit 1
}

if ! command -v tc >/dev/null 2>&1; then
  echo "Warning: tc was not found. Install iproute2 before netem testing." >&2
fi

if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e ".[dev,gui,pdf]"

cat <<'MSG'

Bootstrap complete.

Activate:
  source .venv/bin/activate

Test:
  pytest -q

Launch:
  python3 main.py

Package command:
  catur-jawa
MSG
