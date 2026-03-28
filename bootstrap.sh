#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[paper-radar] Project root: ${ROOT_DIR}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "[paper-radar] Error: ${PYTHON_BIN} not found." >&2
  exit 1
fi

PYTHON_VERSION="$(${PYTHON_BIN} - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

echo "[paper-radar] Detected Python ${PYTHON_VERSION}"

${PYTHON_BIN} - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required.")
PY

if [ ! -d "${VENV_DIR}" ]; then
  echo "[paper-radar] Creating virtual environment at ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

echo "[paper-radar] Upgrading pip"
python -m pip install --upgrade pip

echo "[paper-radar] Installing project with dev dependencies"
python -m pip install -e '.[dev]'

mkdir -p "${ROOT_DIR}/data/raw" "${ROOT_DIR}/data/processed" "${ROOT_DIR}/output" "${ROOT_DIR}/logs"

echo "[paper-radar] Setup complete."
echo "[paper-radar] Activate with: source ${VENV_DIR}/bin/activate"
echo "[paper-radar] First run: paper-radar --dry-run"
