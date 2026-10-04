#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[!] Am creat .env din .env.example. Pune GEMINI_API_KEY daca vrei Gemini."
fi

[ -d .venv ] || python3 -m venv .venv

.venv/bin/python -m pip -q install -r backend/requirements.txt

cd frontend
npm install
npm run build
cd ..

echo "Open http://127.0.0.1:8000  (health: /api/health)"
exec .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
