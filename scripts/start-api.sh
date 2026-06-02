#!/usr/bin/env bash
# Start the API with the project venv (installs deps if needed).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "Creating venv…"
  python3 -m venv venv
fi

echo "Installing / checking Python dependencies…"
./venv/bin/pip install -r requirements.txt

unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy 2>/dev/null || true
export NO_PROXY="localhost,127.0.0.1,api.openai.com,.openai.com"
export PYTHONPATH=src

echo "Using: $(./venv/bin/python -V) at $ROOT/venv/bin/python"
./venv/bin/python -c "import fitz; print('pymupdf OK')" || {
  echo "ERROR: pymupdf (fitz) missing in venv. Run: ./venv/bin/pip install pymupdf"
  exit 1
}

exec ./venv/bin/python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
