#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip -q install -r backend/requirements.txt
echo "Open http://127.0.0.1:8000  (health: /api/health)"
exec .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
