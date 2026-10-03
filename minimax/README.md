# DocuGuide

Evidence-first guide for Moldovan paperwork. Asks clarifying questions, searches only
approved official domains, and builds a cited step-by-step guide with a local LLM (Ollama).

## Run
1. Install Ollama and pull the model: `ollama pull llama3.2:3b` (see `.env.example`).
2. macOS/Linux: `./run.sh`   ·   Windows: `run.bat`
3. Open http://127.0.0.1:8000 (health: /api/health)

## Layout
- `backend/main.py` – FastAPI: domain guard, slot questions, site-filtered search, evidence, LLM.
- `data/slots.json` – clarifying questions per category.
- `data/source_registry.json` – approved domains + authority.
- `frontend/index.html` – single-page UI.
