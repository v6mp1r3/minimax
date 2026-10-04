# DocuGuide — Gemini + Evidence Retrieval

DocuGuide interpretează întrebarea local, caută dovezi relevante în sursele aprobate și face **un singur apel LLM** pentru răspunsul final.

## Important: Gemini este providerul principal

Configurația implicită este:

```env
AI_PROVIDER=gemini
AI_FALLBACK_PROVIDER=none
GEMINI_MODEL=gemini-3.8-flash
GEMINI_THINKING_LEVEL=low
```

Nu mai există fallback automat la Ollama. Astfel, dacă Gemini nu este configurat, aplicația îți spune clar ce lipsește în loc să încerce `127.0.0.1:11434/api/chat` și să producă un 404.

Google AI Studio poate crea/gestiona cheia Gemini API:
https://aistudio.google.com/apikey

După ce creezi cheia, în `.env`:

```env
GEMINI_API_KEY=...
```

## Pornire Windows

Dublu-click pe:

```text
run.bat
```

Apoi:

```text
http://127.0.0.1:8000
```

Verifică înainte de testare:

```text
http://127.0.0.1:8000/api/health
```

Trebuie să vezi:

```json
{
  "provider": "gemini",
  "primary_ok": true
}
```

Dacă `primary_ok` este `false`, uită-te la `gemini_error`.

## Fallback-uri opționale

### OpenRouter

```env
AI_FALLBACK_PROVIDER=openrouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=qwen/qwen3.8-27b:free
```

### Ollama

Doar dacă vrei explicit:

```env
AI_FALLBACK_PROVIDER=ollama
ENABLE_OLLAMA_FALLBACK=true
OLLAMA_MODEL=qwen3:8b
```

și pornești:

```bash
ollama serve
```

În mod implicit este dezactivat.

## Fluxul DocuGuide

```text
Întrebarea
   ↓
routing local
   ↓
keyword + fuzzy/character retrieval
   ↓
surse oficiale + documente locale
   ↓
evidence pack
   ↓
UN SINGUR apel Gemini
   ↓
răspuns structurat + surse
```

Întrebările naturale precum:

> ce documente am nevoie pentru polita medicala

nu cer profil personal și nu întreabă automat „Da/Nu”.

## Documente proprii

Pune PDF/DOCX/TXT/MD/JSON/CSV în:

```text
data/documents/
```

Acestea sunt folosite de retrieverul local.

### Gemini 503/429 handling
The Gemini client retries transient 429/500/502/503/504 responses with exponential backoff. A persistent provider error is surfaced with the actual HTTP status/body instead of a generic Ollama error.
