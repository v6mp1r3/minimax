import json
import os
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE / ".env")
DATA = BASE / "data"
REGISTRY_FILE = DATA / "source_registry.json"

# Small in-memory TTL cache so repeated demo questions are instant.
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "7200"))
_cache: dict = {}
_cache_lock = threading.Lock()

def cache_get(key):
    with _cache_lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    return None

def cache_set(key, value):
    with _cache_lock:
        _cache[key] = (time.time(), value)

# AI providers: Gemini (primary), OpenRouter (secondary), Ollama (local fallback).
# Only the final answer calls an LLM. Query understanding, routing and retrieval are local.
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini").strip().lower()
AI_FALLBACK_PROVIDER = os.getenv("AI_FALLBACK_PROVIDER", "openrouter").strip().lower()
LLM_MAX_PROMPT_CHARS = int(os.getenv("LLM_MAX_PROMPT_CHARS", "14000"))
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))
ENABLE_CLARIFICATIONS = os.getenv("ENABLE_CLARIFICATIONS", "false").strip().lower() == "true"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
GEMINI_THINKING_LEVEL = os.getenv("GEMINI_THINKING_LEVEL", "low").strip().lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
OLLAMA_THINK = os.getenv("OLLAMA_THINK", "false").strip().lower() == "true"
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))


def _gemini_chat(messages, json_mode, temperature, max_tokens, timeout):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY nu este configurată.")
    system_parts = [m["content"] for m in messages if m.get("role") == "system"]
    user_parts = [m["content"] for m in messages if m.get("role") != "system"]
    contents = [{"role": "user", "parts": [{"text": "\n\n".join(user_parts)}]}]
    generation = {"maxOutputTokens": max_tokens}
    # Gemini 3.8 uses thinking levels. Keep the request minimal and avoid
    # deprecated sampling fields such as temperature/top_p/top_k.
    if GEMINI_THINKING_LEVEL in {"low", "medium", "high"}:
        generation["thinkingConfig"] = {"thinkingLevel": GEMINI_THINKING_LEVEL}
    if json_mode:
        generation["responseMimeType"] = "application/json"
    payload = {
        "systemInstruction": {"parts": [{"text": "\n\n".join(system_parts)}]} if system_parts else None,
        "contents": contents,
        "generationConfig": generation,
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent"

    # Google can temporarily return 429/500/502/503/504. Retry with
    # exponential backoff instead of immediately converting a transient
    # provider problem into a DocuGuide 503.
    retryable = {429, 500, 502, 503, 504}
    delays = (1.0, 2.0, 4.0)
    last_status = None
    last_body = ""
    with httpx.Client(timeout=timeout) as client:
        for attempt in range(len(delays) + 1):
            try:
                r = client.post(
                    url,
                    headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
                    json=payload,
                )
            except httpx.HTTPError as exc:
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                    continue
                raise RuntimeError(f"Gemini conexiunea a eșuat după retry-uri: {exc}") from exc

            if r.status_code < 400:
                data = r.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                return "".join(part.get("text", "") for part in parts if isinstance(part, dict)).strip()

            last_status = r.status_code
            last_body = r.text[:1200]
            if r.status_code in retryable and attempt < len(delays):
                time.sleep(delays[attempt])
                continue

            raise RuntimeError(
                f"Gemini a răspuns cu HTTP {last_status}: {last_body}"
            )

    raise RuntimeError(f"Gemini a răspuns cu HTTP {last_status}: {last_body}")


def _openrouter_chat(messages, json_mode, temperature, max_tokens, timeout):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY nu este configurată.")
    payload = {"model": OPENROUTER_MODEL, "messages": messages, "temperature": temperature,
               "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://127.0.0.1:8000",
        "X-Title": "DocuGuide",
    }
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""


def _ollama_chat(messages, json_mode, temperature, max_tokens, timeout):
    payload = {"model": OLLAMA_MODEL, "stream": False, "messages": messages,
               "options": {"temperature": temperature, "num_ctx": OLLAMA_NUM_CTX, "num_predict": max_tokens},
               "think": OLLAMA_THINK}
    if json_mode:
        payload["format"] = "json"
    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "") or ""


def _provider_available(name: str) -> bool:
    if name == "gemini":
        return bool(GEMINI_API_KEY)
    if name == "openrouter":
        return bool(OPENROUTER_API_KEY)
    if name == "ollama":
        # Ollama is opt-in. We never silently fall back to a local server.
        return os.getenv("ENABLE_OLLAMA_FALLBACK", "false").strip().lower() == "true"
    return False


def _provider_chain():
    chain = []
    for name in (AI_PROVIDER, AI_FALLBACK_PROVIDER):
        name = (name or "").strip().lower()
        if name and name not in {"none", "disabled"} and name not in chain and _provider_available(name):
            chain.append(name)
    return chain


def _call_provider(name, messages, json_mode, temperature, max_tokens, timeout):
    if name == "gemini":
        return _gemini_chat(messages, json_mode, temperature, max_tokens, timeout)
    if name == "openrouter":
        return _openrouter_chat(messages, json_mode, temperature, max_tokens, timeout)
    return _ollama_chat(messages, json_mode, temperature, max_tokens, timeout)


def llm_chat(messages, json_mode=False, temperature=0.15, max_tokens=900, timeout=None):
    """One final LLM call per user request. Falls back only if the primary provider fails."""
    last = None
    for provider in _provider_chain():
        try:
            return _call_provider(provider, messages, json_mode, temperature, max_tokens, timeout or LLM_TIMEOUT)
        except Exception as exc:
            last = exc
            continue
    raise RuntimeError(str(last) if last else "Niciun provider AI configurat.")


def provider_status():
    return {
        "primary": AI_PROVIDER,
        "fallback": AI_FALLBACK_PROVIDER,
        "configured": {"gemini": bool(GEMINI_API_KEY), "openrouter": bool(OPENROUTER_API_KEY), "ollama": os.getenv("ENABLE_OLLAMA_FALLBACK", "false").strip().lower() == "true"},
        "models": {"gemini": GEMINI_MODEL, "openrouter": OPENROUTER_MODEL, "ollama": OLLAMA_MODEL},
    }


def llm_label() -> str:
    return f"{AI_PROVIDER} · {GEMINI_MODEL if AI_PROVIDER == 'gemini' else OPENROUTER_MODEL if AI_PROVIDER == 'openrouter' else OLLAMA_MODEL}"

app = FastAPI(title="DocuGuide — Evidence Research Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

SLOTS_FILE = DATA / "slots.json"

class ChatRequest(BaseModel):
    question: str
    category: str = "auto"
    country: str = "auto"
    # Slot answers collected by the clarifying-question flow (client holds the state).
    answers: dict = {}
    # Guide the user is currently looking at (lets follow-up questions refer to it).
    context: dict = {}

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text

def detect_category(question: str) -> str:
    q = question.lower()
    if any(x in q for x in ["erasmus", "erasmus+", "universitate", "burs", "studii", "student", "facultate"]):
        return "education"
    if any(x in q for x in ["chirie", "în chirie", "inchirie", "apartament", "locuință", "locuinta", "contract de închiriere"]):
        return "rent"
    if any(x in q for x in ["mașină", "masina", "automobil", "autoturism", "vehicul", "înmatricul", "inmatricul", "numere", "plăcuțe", "placute", "acte auto", "vămuire", "vamuire", "vamă", "vama", "import auto"]):
        return "auto"
    if any(x in q for x in ["viză", "viza", "permis de ședere", "permis de sedere", "mă mut", "mutare", "mut în", "reloc"]):
        return "relocation"
    if any(x in q for x in ["angajare", "angajat", "contract de muncă", "contract de munca", "job", "salariat"]):
        return "employment"
    if any(x in q for x in ["firmă", "firma", "companie", "societate", "deschid o firmă", "deschid o firma", "srl", "s.r.l",
                            "întreprindere", "intreprindere", "afacere", "afaceri", "persoană juridică", "persoana juridica"]):
        return "business"
    if any(x in q for x in ["medic", "spital", "servicii medicale", "asigurare medicală", "asigurare medicala", "polita medicala", "polita de asigurare", "aoam", "cnam", "asigurat", "asigurata"]):
        return "health"
    return "general"

def detect_country(question: str) -> str:
    q = question.lower()
    countries = {
        "germania": "Germany", "românia": "Romania", "romania": "Romania",
        "italia": "Italy", "franța": "France", "franta": "France",
        "moldova": "Moldova", "spania": "Spain", "austria": "Austria",
        "polonia": "Poland", "belgia": "Belgium"
    }
    for key, value in countries.items():
        if key in q:
            return value
    return "Moldova"

def explicit_country(question: str):
    """Return the country only if the question really names one."""
    q = question.lower()
    for key in ["germania", "românia", "romania", "italia", "franța", "franta",
                "spania", "austria", "polonia", "belgia"]:
        if key in q:
            return detect_country(key)
    return None

def slots_for(category: str):
    """Resolve slot definitions for a category (expanding shared slots)."""
    cfg = load_json(SLOTS_FILE)
    common = cfg["_common"]
    out = []
    for s in cfg.get(category, cfg["general"])["slots"]:
        if isinstance(s, str):
            s = {"key": s, **common[s]}
        out.append(s)
    return out

EU_COUNTRIES = {"germany", "romania", "italy", "france", "spain", "austria", "poland", "belgium"}
NON_EU_HINTS = ["elvetia", "turcia", "sua", "statele unite", "america", "japonia", "china", "rusia",
                "ucraina", "anglia", "marea britanie", "regatul unit", "canada", "coreea", "dubai", "emirate", "georgia"]

def infer_slot(slot: dict, question: str, explicit: str):
    """Return a value for `slot` if the question already states it, else None."""
    q = " " + fold(question) + " "
    if slot.get("auto_from") == "country" and explicit:
        return explicit
    if slot.get("auto_from") == "country_bloc":
        if (explicit or "").lower() in EU_COUNTRIES:
            return "EU"
        if any(h in q for h in NON_EU_HINTS):
            return "NON_EU"
        return None
    if slot["key"] == "citizenships":
        # Read the words right after "cetatenie" so "moldoveneasca si romana" yields both.
        found = set()
        for m_ in re.finditer(r"cetate", q):
            window = q[m_.start(): m_.start() + 90]
            if re.search(r"moldov|\brm\b", window):
                found.add("MD")
            if re.search(r"roman(a|easca|esc)?\b|\bue\b|europea|italian|german|francez|spaniol|polone", window):
                found.add("EU")
        return [v for v in ("MD", "EU") if v in found] or None
    hits = [o["value"] for o in slot["options"] if any(k in q for k in o.get("keywords", []))]
    if slot["type"] == "multi":
        return hits or None  # citizenship stated in the question -> no need to ask again
    return hits[0] if len(hits) == 1 else None

def missing_slots(category: str, question: str, answers: dict, country_hint: str, only=None):
    """Slots we still need; anything the question already says is filled in, not asked."""
    known = dict(answers or {})
    explicit = explicit_country(question)
    if country_hint not in ("auto", "Moldova", None):
        explicit = explicit or country_hint
    missing = []
    for s in slots_for(category):
        if only is not None and s["key"] not in only:
            continue
        if s["key"] in known:
            continue
        value = infer_slot(s, question, explicit)
        if value is not None:
            known[s["key"]] = value
            continue
        missing.append(s)
    return known, missing

def allowed_sources(category: str):
    registry = load_json(REGISTRY_FILE)
    item = registry.get(category, registry["general"])
    return item["domains"]

def domain_guard(question: str):
    """
    Classify whether a question belongs to DocuGuide's administrative domain.
    We deliberately use deterministic keyword signals first so clearly unrelated
    questions never reach web search or the answer model.
    """
    q = clean_text(question).lower()

    # Strong off-topic signals. These are intentionally conservative:
    # only reject when the question is clearly a different task.
    off_topic_patterns = [
        r"\bscrie(ți|te)?\s+(un\s+)?cod\b",
        r"\bc\+\+\b", r"\bpython\b", r"\bjavascript\b", r"\bjava\b",
        r"\bc#\b", r"\blua\b(?=.*\b(cod|script|program\w*)\b)", r"\broblox\b",
        r"\blinked\s*list\b", r"\balgoritm(ul)?\b",
        r"\bprogramare\b", r"\bdebug\b", r"\bbug\b",
        r"\bhtml\b", r"\bcss\b", r"\bsql\b",
        r"\bpoezie\b", r"\beseu\b", r"\bcompunere\b",
        r"\brețetă\b", r"\breteta\b", r"\bjoc\b",
    ]

    admin_patterns = [
        r"\bdocument(e|e?le)?\b", r"\bact(e|ele)?\b", r"\bbuletin\b",
        r"\bpașaport\b", r"\bpasaport\b", r"\bcertificat\b",
        r"\bpermis\b", r"\bviză\b", r"\bviza\b", r"\bședere\b",
        r"\bsedere\b", r"\bdomiciliu\b", r"\badministrativ\b",
        r"\bprocedur", r"\bînscriere\b", r"\binscriere\b",
        r"\buniversitate\b", r"\berasmus\b", r"\bburs", r"\bstudii\b",
        r"\bchirie\b", r"\bînchir", r"\binchir", r"\bapartament\b",
        r"\bcontract\b", r"\bangajare\b", r"\bjob\b", r"\bemployment\b",
        r"\bfirmă\b", r"\bfirma\b", r"\bsrl\b", r"\bs\.r\.l\b", r"\bîntreprindere", r"\bintreprindere", r"\bafacere", r"\bcompanie\b", r"\bautoriza",
        r"\bmașin[aă]\b", r"\bmasin[aă]\b", r"\bautomobil\b", r"\bautoturism\b",
        r"\bvehicul\b", r"\bînmatricul", r"\binmatricul", r"\bnumere\b",
        r"\bplăcuțe\b", r"\bplacute\b", r"\bacte auto\b", r"\bvămuire\b", r"\bvamuire\b",
        r"\bvam[aă]\b", r"\bimport auto\b", r"\badus[aă]?\s+(din|dintr-un|dintr-o)\b",
        r"\bservicii publice\b", r"\bstare civilă\b", r"\bstare civila\b",
        r"\bmutare\b", r"\breloc", r"\bcălător", r"\bcalator",
        r"\bambasad", r"\bconsulat\b", r"\bmedic\b", r"\basigurare\b",
        r"\bacte necesare\b", r"\bce trebuie să fac\b", r"\bce trebuie sa fac\b",
        r"\bunde trebuie să merg\b", r"\bunde trebuie sa merg\b",
        r"\bcât costă\b", r"\bcat costa\b", r"\bcât durează\b", r"\bcat dureaza\b",
    ]

    if any(re.search(p, q) for p in off_topic_patterns):
        # An explicit administrative phrase wins over a generic word like "contract".
        if not any(re.search(p, q) for p in admin_patterns):
            return {
                "allowed": False,
                "reason": "Întrebarea nu pare să fie despre documente sau proceduri administrative.",
                "category": "other"
            }

    # "documente", "acte", "cât costă"... appear in any question ("ce documente am nevoie pentru un kebab"),
    # so on their own they are NOT proof of an administrative topic: only specific topics are.
    generic = [
        r"\bdocument(e|e?le)?\b", r"\bact(e|ele)?\b", r"\bprocedur", r"\bacte necesare\b",
        r"\bce trebuie să fac\b", r"\bce trebuie sa fac\b", r"\bunde trebuie să merg\b", r"\bunde trebuie sa merg\b",
        r"\bcât costă\b", r"\bcat costa\b", r"\bcât durează\b", r"\bcat dureaza\b",
        r"\bcontract\b", r"\badministrativ\b", r"\bjob\b",
    ]
    # specific topics also match inflected forms ("buletinul", "mașinii"): drop the closing word boundary
    specific = [p[:-2] if p.endswith("\\b") else p for p in admin_patterns if p not in generic]
    if any(re.search(p, q) for p in specific):
        return {"allowed": True, "reason": "", "category": "administrative"}

    # Ask a tiny local classification call only for ambiguous questions.
    # This keeps the deterministic guard fast while allowing natural questions
    # such as "Vreau să plec la facultate în Germania, ce fac?"
    return {"allowed": "ambiguous", "reason": "", "category": "unknown"}


def get_domain_decision(question: str):
    """Purely local domain routing. It deliberately never calls an LLM.
    This guarantees one provider request maximum for a normal question."""
    decision = domain_guard(question)
    if decision["allowed"] in (True, False):
        return decision
    q = fold(question)
    # Natural-language administrative signals. This is intentionally broad; the
    # evidence/domain checks later decide whether a useful answer can be produced.
    natural_admin = [
        "ce acte", "ce document", "ce hart", "ce trebuie", "cum obtin", "cum fac", "unde depun",
        "unde merg", "cat costa", "cat dureaza", "cum verific", "cum solicit", "cum inregistrez",
        "cum deschid", "cum schimb", "cum declar", "cum aplic", "vreau sa obtin", "am nevoie de",
        "pierdut", "reinno", "reinoi", "cerere", "formular", "taxa", "certificat", "adeverinta",
        "polita", "asigurare", "cnam", "aoam", "buletin", "pasaport", "srl", "viza", "permis",
    ]
    if any(x in q for x in natural_admin):
        return {"allowed": True, "reason": "Întrebare administrativă detectată local.", "category": "administrative"}
    return {
        "allowed": False,
        "reason": "Întrebarea nu pare să fie despre documente sau proceduri administrative.",
        "category": "other",
    }

def build_queries(question: str, category: str, country: str):
    q = clean_text(question)
    queries = [q]
    if category == "education":
        queries += [
            f"Erasmus student mobility required documents {country}",
            f"Erasmus application documents {country}",
        ]
    elif category == "rent":
        queries += [
            f"închiriere apartament acte contract chirie {country}",
            f"contract de locațiune documente {country}",
        ]
    elif category == "relocation":
        queries += [
            f"official documents relocation residence {country}",
            f"official residence permit documents {country}",
        ]
    elif category == "auto":
        queries += [
            f"înmatriculare automobil import Germania Moldova acte {country}",
            f"acte necesare înmatriculare mașină importată {country}",
            f"vămuire automobil importat documente {country}",
        ]
    elif category == "employment":
        queries += [
            f"acte angajare contract de muncă {country}",
            f"documente salariat {country}",
        ]
    elif category == "business":
        queries += [
            f"deschidere firmă documente {country}",
            f"înregistrare companie acte {country}",
        ]
    elif category == "health":
        queries += [
            f"polița medicală AOAM acte documente {country}",
            f"CNAM asigurare obligatorie asistență medicală documente {country}",
            f"statut asigurat poliță medicală verificare {country}",
        ]
    else:
        queries += [
            f"official documents requirements {country} {q}",
        ]
    return list(dict.fromkeys(queries))

def domain_allowed(url: str, allowed):
    try:
        host = (urlparse(url).hostname or "").lower()
        return any(host == x["domain"] or host.endswith("." + x["domain"]) for x in allowed)
    except Exception:
        return False

def authority_for(url: str, allowed):
    host = (urlparse(url).hostname or "").lower()
    for item in allowed:
        if host == item["domain"] or host.endswith("." + item["domain"]):
            return item["authority"], item["label"]
    return 0, "Necunoscut"

STOPWORDS = set("care este sunt pentru despre cand unde cum vreau trebuie aveam avea nevoie ajutor acte actele documente documentele necesare ce imi mine plec iau fac face dintr din intr catre pana acest aceasta" .split())
CATEGORY_TERMS = {
    "education": ["erasmus", "mobilit", "student", "burs", "relatii internationale"],
    "relocation": ["viza", "sedere", "relocar"],
    "rent": ["chiri", "locatiune", "contract"],
    "auto": ["inmatricul", "vamu", "automobil"],
    "employment": ["angaj", "munca", "contract"],
    "business": ["inregistr", "societate", "firma"],
    "health": ["medic", "asigurar", "cnam", "aoam", "polita", "asigurat"],
}

def fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

def stems_for(question: str, category: str):
    words = re.findall(r"[a-z0-9]+", fold(question))
    stems = {w[:5] for w in words if len(w) >= 4 and w not in STOPWORDS}
    stems |= {t[:5] for t in CATEGORY_TERMS.get(category, [])}
    return stems

def relevance(text: str, stems) -> float:
    t = fold(text)
    return sum(min(t.count(st), 5) ** 0.5 for st in stems)

def excerpt(text: str, stems, limit: int = 2500, window: int = 600, stride: int = 400) -> str:
    """Most relevant windows of a page (page starts are mostly menus)."""
    if len(text) <= limit:
        return text
    wins = [(i, text[i:i + window]) for i in range(0, len(text), stride)]
    top = sorted(wins, key=lambda w: -relevance(w[1], stems))[: max(1, limit // window)]
    return " … ".join(w[1] for w in sorted(top))

def _site_search(domain: str, queries):
    """Search one approved domain with a site: filter. Returns raw ddgs hits.
    The search engine is flaky (rate limits, empty answers), so an empty answer is retried once."""
    hits = []
    for query in queries:
        for attempt in (0, 1):
            try:
                with DDGS(timeout=10) as ddgs:
                    got = list(ddgs.text(f"site:{domain} {query}", max_results=4))
            except Exception:
                got = []
            if got:
                hits.extend(got)
                break
            time.sleep(0.8)
    return hits

LOCAL_DOCS_DIR = DATA / "documents"


def _extract_local_file(path: Path) -> str:
    try:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".log"}:
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".json":
            obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
            return json.dumps(obj, ensure_ascii=False, indent=2)
        if suffix == ".csv":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
                return "\n".join((page.extract_text() or "") for page in PdfReader(str(path)).pages)
            except Exception:
                return ""
        if suffix == ".docx":
            try:
                from docx import Document
                return "\n".join(p.text for p in Document(str(path)).paragraphs)
            except Exception:
                return ""
    except Exception:
        return ""
    return ""


def _char_ngrams(text: str, n=3):
    t = re.sub(r"[^a-z0-9]+", " ", fold(text))
    return {t[i:i+n] for i in range(max(0, len(t)-n+1)) if " " not in t[i:i+n]}


def _hybrid_score(query: str, text: str) -> float:
    q_words = {w for w in re.findall(r"[a-z0-9]+", fold(query)) if len(w) >= 3 and w not in STOPWORDS}
    t_words = set(re.findall(r"[a-z0-9]+", fold(text)))
    lexical = len(q_words & t_words) / max(len(q_words), 1)
    qgrams, tgrams = _char_ngrams(query), _char_ngrams(text[:12000])
    fuzzy = len(qgrams & tgrams) / max(len(qgrams), 1)
    return 0.72 * lexical + 0.28 * fuzzy


def search_local_documents(question: str, category: str):
    if not LOCAL_DOCS_DIR.exists():
        return []
    results = []
    for path in LOCAL_DOCS_DIR.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".json", ".csv", ".pdf", ".docx"}:
            continue
        text = _extract_local_file(path)
        if not text.strip():
            continue
        score = _hybrid_score(question, text)
        # Category terms are a second signal so a short user question still finds the right file.
        score += 0.12 * _hybrid_score(" ".join(CATEGORY_TERMS.get(category, [])), text)
        if score < 0.08:
            continue
        stems = stems_for(question, category)
        body = excerpt(text, stems, limit=2200) if text else ""
        results.append({
            "title": path.name,
            "url": "local://" + path.relative_to(BASE).as_posix(),
            "snippet": clean_text(body[:900]),
            "authority": 4,
            "organization": "Document local",
            "relevance": score,
            "fetched": True,
            "text": body,
        })
    return sorted(results, key=lambda x: -x["relevance"])[:8]


def search_web(question: str, category: str, country: str):
    """Hybrid retrieval: local user documents + approved official web sources.
    Retrieval is deterministic/local; no LLM is used here."""
    cache_key = ("search", question, category, country)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    local = search_local_documents(question, category)
    allowed = allowed_sources(category)
    queries = build_queries(question, category, country)[:4]
    hits = []
    with ThreadPoolExecutor(max_workers=max(1, len(allowed))) as pool:
        per_domain = list(pool.map(lambda d: _site_search(d["domain"], queries), allowed))
    seen = set()
    for domain_hits in per_domain:
        for r in domain_hits:
            url = r.get("href") or r.get("url") or ""
            if not url or url in seen or not domain_allowed(url, allowed):
                continue
            seen.add(url)
            authority, label = authority_for(url, allowed)
            hits.append({
                "title": clean_text(r.get("title", "")),
                "url": url,
                "snippet": clean_text(r.get("body", "")),
                "authority": authority,
                "organization": label,
            })
    stems = stems_for(question, category)
    for r in hits:
        r["relevance"] = relevance(f"{r['title']} {r['url']} {r['snippet']}", stems) + _hybrid_score(question, f"{r['title']} {r['snippet']}")
    hits.sort(key=lambda x: (-x["relevance"], -x["authority"]))
    results = local[:4] + hits[:10]
    results.sort(key=lambda x: (-x.get("relevance", 0), -x.get("authority", 0)))
    results = results[:10]
    if results:
        cache_set(cache_key, results)
    return results

def extract_content(soup) -> str:
    """Main readable content only: drops menus/breadcrumbs (blocks that are mostly links)."""
    for tag in soup(["script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    root = soup.select_one("main, [role=main], article, .content, #content") or soup.body or soup
    blocks, seen = [], set()
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th", "dd"]):
        if el.find(["p", "li", "td", "th"]):  # container of other blocks; its children are visited
            continue
        text = clean_text(el.get_text(" "))
        is_heading = el.name in ("h1", "h2", "h3", "h4")
        # Short items matter ("master;", "– nu se pot înscrie:"); menus are removed by the link-ratio test below.
        if len(text) < 5 or text in seen:
            continue
        link_len = sum(len(clean_text(a.get_text(" "))) for a in el.find_all("a"))
        if not is_heading and link_len / max(len(text), 1) > 0.6:
            continue
        seen.add(text)
        blocks.append(f"## {text}" if is_heading else text)
    return "\n".join(blocks)

def fetch_page(url: str):
    if url.startswith("local://"):
        path = BASE / url[len("local://"):]
        text = _extract_local_file(path)
        return path.name, text[:12000]
    cached = cache_get(("page", url))
    if cached is not None:
        return cached
    headers = {"User-Agent": "DocuGuide-Hackathon/0.1"}
    for timeout in (8, 15):  # one slow answer from an official site should not count as "unreachable"
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
                r = client.get(url)
                r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            title = clean_text(soup.title.get_text(" ")) if soup.title else ""
            text = extract_content(soup)
            out = (title, text[:12000])
            if text:
                cache_set(("page", url), out)
            return out
        except Exception:
            continue
    return "", ""

def evidence_pack(results, question: str = "", category: str = "general"):
    """Fetch the top pages in parallel and keep source ids stable."""
    stems = stems_for(question, category)
    top = results[:5]
    with ThreadPoolExecutor(max_workers=5) as pool:
        pages = list(pool.map(lambda it: fetch_page(it["url"]), top))
    ranked = []
    for item, (title, text) in zip(top, pages):
        item["fetched"] = bool(text)
        body = excerpt(text, stems) if text else item["snippet"][:1200]
        if body:
            ranked.append((relevance(body, stems), item, title, bool(text), body))
    # Keep only pages that actually mention the question's terms (if any do).
    if any(r[0] > 0 for r in ranked):
        ranked = [r for r in ranked if r[0] > 0]
    ranked.sort(key=lambda r: (-r[0], -r[1]["authority"]))
    evidence = []
    for _, item, title, fetched, body in ranked:
        evidence.append({
            "id": len(evidence) + 1,
            "title": title or item["title"],
            "url": item["url"],
            "organization": item["organization"],
            "authority": item["authority"],
            "fetched": fetched,
            "text": body,
        })
    return evidence

def grounded(name: str, texts) -> bool:
    """True if the significant words of `name` appear in the cited source text."""
    words = [w[:5] for w in re.findall(r"[a-z0-9]+", fold(name)) if len(w) >= 5 and w not in STOPWORDS]
    if not words:
        return False
    blob = fold(" ".join(texts))
    return all(w in blob for w in words)

def sanitize_answer(answer: dict, evidence: list) -> dict:
    """Enforce the evidence rule in code, not just in the prompt.
    A small local model happily invents requirements and cites sources for them,
    so a claim stays 'confirmed' only if its words occur in the cited source text."""
    n_sources = len(evidence)
    by_id = {e["id"]: e["text"] for e in evidence}
    if not isinstance(answer, dict):
        answer = {"summary": str(answer)}
    answer.setdefault("summary", "")
    for k in ("clarifying_questions", "documents", "steps", "warnings", "contradictions"):
        if not isinstance(answer.get(k), list):
            answer[k] = []
    answer["clarification_needed"] = False

    def valid_ids(ids):
        return [i for i in (ids if isinstance(ids, list) else []) if isinstance(i, int) and 1 <= i <= n_sources]

    dropped_docs = dropped_steps = 0
    docs = []
    for d in answer["documents"]:
        if not isinstance(d, dict) or not d.get("name"):
            continue
        d["sources"] = valid_ids(d.get("sources"))
        if d.get("status") not in ("required", "possible", "recommended", "unknown"):
            d["status"] = "unknown"
        if not grounded(d["name"], [by_id[i] for i in d["sources"]]):
            dropped_docs += 1  # not in the cited sources -> not shown
            continue
        if d["status"] == "required" and not d["sources"]:
            d["status"] = "unknown"
        docs.append(d)
    answer["documents"] = docs

    steps = []
    for st in answer["steps"]:
        if not (isinstance(st, dict) and st.get("title")):
            continue
        st["sources"] = valid_ids(st.get("sources"))
        if not grounded(st["title"], [by_id[i] for i in st["sources"]]):
            dropped_steps += 1
            continue
        steps.append(st)
    answer["steps"] = steps
    answer["contradictions"] = [c for c in answer["contradictions"] if isinstance(c, dict)]

    dropped = dropped_docs + dropped_steps
    if dropped:
        answer["warnings"].insert(0, f"{dropped} elemente propuse de model au fost eliminate pentru că nu apar în sursele oficiale găsite.")
    if not docs and not steps:
        answer["summary"] = ("Sursele oficiale găsite nu descriu documentele sau pașii exacți pentru această situație, "
                             "așa că nu pot construi un ghid de încredere. Consultă direct sursele de mai jos.")
    return answer

def profile_text(profile: dict) -> str:
    if not profile:
        return "(none)"
    return "\n".join(f"- {k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in profile.items())

def make_prompt(question, category, country, evidence, profile=None):
    sources = []
    for e in evidence:
        sources.append(
            f"[SOURCE {e['id']}]\n"
            f"Organization: {e['organization']}\n"
            f"Authority score: {e['authority']}/5\n"
            f"Title: {e['title']}\n"
            f"URL: {e['url']}\n"
            f"Evidence: {e['text']}\n"
        )
    return f"""
You are DocuGuide, not a generic chatbot. You are an evidence-based administrative guide.

USER QUESTION:
{question}

DETECTED CONTEXT:
category={category}
country={country}

USER PROFILE (already collected from the user, do NOT ask for it again; values "unknown" mean the user did not know):
{profile_text(profile)}
Tailor the guide to this profile. If the profile changes a requirement (e.g. EU citizens often need no visa), say so and cite a source; if no source covers it, mark it unknown.

SOURCE POLICY:
Only use the supplied sources. Do not invent requirements.
Prefer authority 5 sources.
If a requirement is not explicitly supported, do NOT call it required.
Distinguish:
- required: explicitly required by a source
- possible: may depend on institution/person/landlord
- recommended: useful but not established as mandatory
- unknown: cannot be confirmed from evidence

If sources disagree, report the disagreement instead of silently choosing.
Every document and step MUST be stated in the SOURCE MATERIAL below. Do not use general knowledge. If the sources do not describe the procedure or the documents, return empty "documents" and "steps" lists and say so in "summary". Never turn a menu item, link title or unrelated service into a step.
Do not ask the user follow-up questions just to make the answer easier. Use the information in the question and sources. If a detail truly changes the result and is missing, explain the dependency in warnings instead of blocking the answer. Always set "clarification_needed" to false.

For every cost, duration, institution, address and link: copy it ONLY from the sources. If a source does not state it, use null. Never guess an amount or a number of days. "link" must be one of the source URLs.
"depends_on_step" is the 1-based number of the step that must be finished before this one (or null).

Return ONLY valid JSON with this shape:
{{
  "summary": "short Romanian answer",
  "clarification_needed": false,
  "clarifying_questions": [],
  "documents": [
    {{
      "name": "document",
      "status": "required|possible|recommended|unknown",
      "reason": "why",
      "where_to_get": "institution or null",
      "sources": [1]
    }}
  ],
  "steps": [
    {{
      "title": "step",
      "description": "what to do",
      "where": "institution/office or null",
      "cost": "e.g. 250 MDL, or null",
      "duration": "e.g. 10 zile lucrătoare, or null",
      "depends_on_step": null,
      "link": "source URL or null",
      "sources": [1]
    }}
  ],
  "warnings": ["important uncertainty"],
  "contradictions": [
    {{
      "topic": "requirement",
      "source_a": 1,
      "source_b": 2,
      "description": "what differs"
    }}
  ]
}}

SOURCE MATERIAL:
{chr(10).join(sources)}
""".strip()

def parse_json_lenient(text: str):
    """json.loads, but also rescue answers cut off by the output limit or wrapped in prose."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    start = (text or "").find("{")
    if start < 0:
        return None
    t = text[start:]
    tries = 0
    for i in range(len(t) - 1, 0, -1):
        if t[i] not in "}]\"0123456789el":  # plausible end of a complete value
            continue
        tries += 1
        if tries > 400:
            break
        cand, stack, in_str, esc = t[: i + 1], [], False, False
        for ch in cand:
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append("}" if ch == "{" else "]")
            elif ch in "}]" and stack:
                stack.pop()
        if in_str:
            continue
        try:
            obj = json.loads(cand.rstrip().rstrip(",") + "".join(reversed(stack)))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None

def call_ai(prompt):
    """Answer step (name kept for compatibility): returns the parsed JSON answer from the active provider."""
    content = llm_chat(
        [{"role": "system", "content": "Return valid JSON only. Answer in Romanian. Keep every text field short."},
         {"role": "user", "content": prompt}],
        json_mode=True, temperature=0.05, max_tokens=2000, timeout=240,
    ) or "{}"
    parsed = parse_json_lenient(content)
    if parsed is not None:
        return parsed
    return {
        "summary": "",
        "clarification_needed": False,
        "clarifying_questions": [],
        "documents": [],
        "steps": [],
        "warnings": [],
        "contradictions": [],
    }

BOILERPLATE = ("cookie", "©", "sugestiile si propunerile", "toate drepturile", "politica de confidentialitate", "filtru")

GENERIC_QUESTION_WORDS = set("docum acte nevoi trebu neces avea fac fie sunt lipse cere obtin obtine cumpar cumpara ghid pasi pasii "
                             "procedura procedur proces cost costa costul termen zile desch inchi vreau pleca merg mers aduce adus aduc "
                             "schim muta mut cauta caut aplic aplica inscr depun depus primi prime primesc obtin".split())

def topic_stems(question: str, category: str):
    """Stems of what the question is actually ABOUT (generic admin words and category hints removed)."""
    words = re.findall(r"[a-z0-9]+", fold(question))
    stems = {w[:5] for w in words if len(w) >= 4 and w not in QUESTION_STOP}
    stems -= {t[:5] for t in CATEGORY_TERMS.get(category, [])}
    return {st for st in stems if st not in GENERIC_QUESTION_WORDS}

def subject_in_sources(question: str, category: str, evidence: list) -> bool:
    """False when the question's own subject (e.g. "kebab") occurs in none of the official pages found.
    Only applies to questions with no recognised administrative topic (category "general"): a question
    already recognised as business / auto / education ... is on-topic by definition."""
    if category != "general":
        return True
    stems = topic_stems(question, category)
    if not stems:
        return True
    blob = fold(" ".join(e["text"] for e in evidence))
    hits = sum(1 for st in stems if st in blob)
    # one shared word ("licență" on a page about university degrees) is not enough for a multi-word subject
    return hits >= max(1, (len(stems) + 1) // 2)

def build_extracts(evidence: list, question: str, category: str, limit: int = 3):
    """Relevant passages straight from the official pages: used when no structured guide can be trusted.
    Only passages that really match the question's terms are kept (no menus, cookie banners, footers)."""
    stems = {st for st in stems_for(question, category)}
    out = []
    for e in evidence:
        best, best_score = None, 0
        for i in range(0, len(e["text"]), 450):
            win = e["text"][i:i + 700].strip()
            if not win or any(b in fold(win) for b in BOILERPLATE):
                continue
            score = sum(1 for st in stems if st in fold(win))
            if score > best_score:
                best, best_score = win, score
        if best and best_score >= 2:
            out.append({"id": e["id"], "text": best, "url": e["url"], "source": e["title"], "_score": best_score})
    out.sort(key=lambda x: -x["_score"])
    for x in out:
        x.pop("_score")
    return out[:limit]

CARDS_DIR = DATA / "cards"

def load_cards():
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(CARDS_DIR.glob("*.json"))] if CARDS_DIR.exists() else []

def find_card(category: str, question: str, profile: dict):
    """First curated card whose category, keywords and slot conditions all match."""
    q = fold(question)
    for card in load_cards():
        if card["category"] != category:
            continue
        if card.get("match_hints") and not any(h in q for h in card["match_hints"]):
            continue
        ok = True
        for key, allowed in (card.get("applies_when") or {}).items():
            val = str(profile.get(key, "")).split(":")[0].strip()
            if val not in allowed:
                ok = False
        if ok:
            return card
    return None

def card_for_slots(category: str, question: str):
    """Card that will answer this question (by category + keywords); it decides which slots matter."""
    q = fold(question)
    for card in load_cards():
        if card["category"] == category and (not card.get("match_hints") or any(h in q for h in card["match_hints"])):
            return card
    return None

def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", fold(t)).strip()

def verify_card(card: dict):
    """Re-fetch every source page and check each quote is still there.
    Returns ({item_id: 'confirmed'|'changed'|'unreachable'}, {source_key: page_ok}, {item_id: where_confirmed})."""
    urls = {k: v["url"] for k, v in card["sources"].items()}
    with ThreadPoolExecutor(max_workers=max(1, len(urls))) as pool:
        texts = dict(zip(urls, pool.map(lambda u: _norm(fetch_page(u)[1]), urls.values())))
    status, where_ok = {}, {}
    for item in card["documents"] + card["steps"]:
        text = texts.get(item["source"], "")
        quotes = [item["quote"]] if "quote" in item else item["quotes"]
        if not text:
            status[item["id"]] = "unreachable"
        elif all(_norm(q) in text for q in quotes):
            status[item["id"]] = "confirmed"
        else:
            status[item["id"]] = "changed"
        # a "where to get it" value is shown as fact only if the page itself says it
        wq = item.get("where_quote")
        where_ok[item["id"]] = bool(wq and text and _norm(wq) in text)
    return status, {k: bool(t) for k, t in texts.items()}, where_ok

def card_answer(card: dict, profile: dict | None = None):
    status, page_ok, where_ok = verify_card(card)
    keys = list(card["sources"])
    sid = {k: i + 1 for i, k in enumerate(keys)}
    label = {"confirmed": "Confirmat acum pe pagina oficială", "changed": "Pagina oficială s-a schimbat — verifică manual",
             "unreachable": "Nu am putut deschide pagina oficială acum; ultima verificare: " + card["last_verified"]}
    docs = [{
        "name": d["name"], "status": d["status"] if status[d["id"]] != "changed" else "unknown",
        "reason": label[status[d["id"]]], "where_to_get": d.get("where_to_get") if where_ok[d["id"]] else None,
        "sources": [sid[d["source"]]], "quote": d["quote"], "check": status[d["id"]],
    } for d in card["documents"]]
    steps = [{
        "title": st["title"], "description": st["description"], "where": st.get("where"),
        "cost": st.get("cost"), "duration": st.get("duration"), "depends_on_step": st.get("depends_on_step"),
        "link": card["sources"][st["source"]]["url"], "sources": [sid[st["source"]]],
        "quote": st["quotes"][0], "quotes": st["quotes"], "check": status[st["id"]],
    } for st in card["steps"]]
    n_ok = sum(v == "confirmed" for v in status.values())
    warnings = ["Neconfirmat în surse: " + x for x in card.get("unconfirmed", [])]
    cit = (profile or {}).get("citizenships")
    note = card.get("profile_notes", {}).get("citizenships")
    if note and cit:
        cit = cit if isinstance(cit, list) else [cit]
        has_eu = any(str(c).split(":")[0] == "EU" for c in cit)
        warnings.insert(0, note["has_EU"] if has_eu else note["no_EU"])
    if n_ok < len(status):
        warnings.insert(0, f"Doar {n_ok} din {len(status)} elemente au putut fi confirmate acum pe paginile oficiale.")
    answer = {"summary": card["summary"], "clarification_needed": False, "clarifying_questions": [],
              "documents": docs, "steps": steps, "warnings": warnings, "contradictions": []}
    sources = [{"id": sid[k], "title": v["title"], "url": v["url"], "organization": v["organization"],
                "authority": 5, "fetched": page_ok[k]} for k, v in card["sources"].items()]
    return answer, sources, f"{n_ok}/{len(status)}"


QUESTION_STOP = set(STOPWORDS) | set("unde cand cine cui cum iau lua pot putea poti sunt pentru documentul document documente documentul "
                                     "sa de la ce un o si sau din cat mai fi este era ceva pentru despre care".split())
INTENT_WHERE = ("unde", "de la cine", "de la ce", "cine", "cui", "de la care")
INTENT_COST = ("cat costa", "cost", "tarif", "taxa", "pret", "cat platesc", "plata")
INTENT_TIME = ("cat dureaza", "durata", "termen", "cat timp", "cand", "zile", "cat se asteapta")

def _qstems(text: str):
    words = re.findall(r"[a-z0-9]+", fold(text))
    return {w[:5] for w in words if len(w) >= 4 and w not in QUESTION_STOP}

def _item_text(item: dict) -> str:
    parts = [item.get("name") or item.get("title") or "", item.get("description", "")]
    parts += [item["quote"]] if "quote" in item else item.get("quotes", [])
    return fold(" ".join(parts))

def best_item(card: dict, question: str):
    """(item, kind, score) for the card document/step the question talks about.
    Cost/time questions look at steps first; others at documents first."""
    q = fold(question)
    stems = _qstems(question)
    money = any(k in q for k in INTENT_COST + INTENT_TIME)
    groups = (("step", card["steps"]), ("doc", card["documents"])) if money else (("doc", card["documents"]), ("step", card["steps"]))
    best = (None, None, 0)
    for kind, items in groups:
        for it in items:
            text = _item_text(it)
            n = sum(1 for st in stems if st in text)
            if n and any(k in q for k in INTENT_COST) and any(w in text for w in ("drepturile", "tax", "cost", "grant", "tarif", " lei")):
                n += 1
            if n > best[2]:
                best = (it, kind, n)
    return best

def general_answer(card: dict, item, question: str, where: str = ""):
    """Helpful general-knowledge answer for a follow-up the official sources do not cover.
    Always shown to the user as NOT coming from an official source."""
    ctx = ""
    if item is not None:
        quotes = [item["quote"]] if "quote" in item else item.get("quotes", [])
        facts = [item.get("description") or item.get("name") or ""]
        if item.get("cost"):
            facts.append(f"Cost oficial: {item['cost']}")
        if item.get("duration"):
            facts.append(f"Durată oficială: {item['duration']}")
        ctx = (f"Element din ghid: {item.get('name') or item['title']}\n"
               f"Fapte oficiale (din sursa verificată): {' | '.join(f for f in facts if f)}\n"
               f"Citat din sursă: \"{quotes[0] if quotes else ''}\"\n")
    prompt = f"""Utilizatorul urmărește ghidul: «{card['title']}».
{ctx}Întrebarea utilizatorului: {question}

Dă un răspuns util și concret, în română (maximum 6 propoziții sau o listă scurtă de puncte).
Reguli:
- Folosește cunoștințe generale. NU inventa reguli, termene, sume sau cerințe specifice ale unei instituții.
- Nu contrazice niciodată faptele oficiale de mai sus; completează-le doar.
- Dacă lucrul depinde de instituție, spune asta{f' și recomandă să întrebe la: {where}' if where else ''}.
- Dacă nu ești sigur sau întrebarea cere o permisiune/regulă a unei instituții, spune clar că nu știi și cui să ceară confirmarea (nu afirma că „se poate” sau „nu se poate”).
- Nu spune că informația provine dintr-o sursă oficială."""
    try:
        text = llm_chat(
            [{"role": "system", "content": "Ești DocuGuide, asistent pentru documente și proceduri administrative în Republica Moldova. Răspunzi scurt, clar și practic, în română."},
             {"role": "user", "content": prompt}],
            temperature=0.3, max_tokens=350, timeout=150,
        ).strip()
        return text or None
    except Exception:
        return None

CONTENT_CUES = ("contin", "cum scriu", "cum completez", "cum fac", "cum obtin", "exemplu", "ce este", "ce inseamn",
                "de ce", "ce trebuie", "ce ar trebui", "ce informat", "cum ")

def is_followup(card: dict, question: str) -> bool:
    """True when the message continues the guide on screen (about one of its items, or a general
    question in the same area). False for a new topic that has its own guide or is off-topic."""
    if domain_guard(question)["allowed"] is False:
        return False
    if any(fold(t) in fold(question) for g in card.get("glossary", []) for t in g["terms"]):
        return True
    _, _, n = best_item(card, question)
    other = card_for_slots(detect_category(question), question)
    if other and other["id"] != card["id"] and n < 3:
        return False
    return n >= 1 or detect_category(question) in ("general", card["category"])

def followup_answer(card: dict, question: str):
    q = fold(question)
    status, page_ok, where_ok = verify_card(card)
    src = lambda it: card["sources"][it["source"]]
    for g in card.get("glossary", []):
        if any(fold(t) in q for t in g["terms"]):
            meta = card["sources"][g["source"]]
            text = _norm(fetch_page(meta["url"])[1])
            ok = bool(text) and all(_norm(x) in text for x in g["quotes"])
            return {"title": g["title"], "facts": [g["text"]], "unconfirmed": [] if ok else ["Pagina oficială nu a putut fi confirmată acum; verifică manual."],
                    "hint": None, "general": None,
                    "quotes": [{"text": x, "url": meta["url"], "source": meta["title"]} for x in g["quotes"]] if ok else [],
                    "links": [{"label": meta["title"], "url": meta["url"]}]}
    item, kind, n = best_item(card, question)
    want_where = any(k in q for k in INTENT_WHERE)
    want_cost = any(k in q for k in INTENT_COST)
    want_time = any(k in q for k in INTENT_TIME)
    wants_content = any(k in q for k in CONTENT_CUES) and not want_where
    out = {"title": None, "facts": [], "unconfirmed": [], "hint": None, "quotes": [], "links": [], "general": None}

    def quote_entries(it):
        qs = [it["quote"]] if "quote" in it else it["quotes"]
        if status[it["id"]] != "confirmed":
            out["unconfirmed"].append("Pagina oficială nu a putut fi confirmată acum pentru acest element; verifică manual.")
            return []
        return [{"text": t, "url": src(it)["url"], "source": src(it)["title"]} for t in qs]

    n_stems = max(len(_qstems(question)), 1)
    if item is not None and not (n >= 3 or n / n_stems >= 0.6):
        item = None  # only a weak word overlap: do not pretend the guide answers this
    if item is None:
        # nothing in the guide matches: look for passages in the official pages themselves
        stems = _qstems(question)
        for key, meta in card["sources"].items():
            text = fetch_page(meta["url"])[1]
            if not text or not stems:
                continue
            wins = [(i, text[i:i + 500]) for i in range(0, len(text), 350)]
            scored = sorted(wins, key=lambda w: -sum(1 for st in stems if st in fold(w[1])))
            top = [w for w in scored[:1] if sum(1 for st in stems if st in fold(w[1])) >= 3]
            for _, t in top:
                out["quotes"].append({"text": t.strip(), "url": meta["url"], "source": meta["title"]})
        if out["quotes"]:
            out["title"] = "Ce apare în sursa oficială"
            out["facts"].append("Nu am găsit exact acest lucru în ghidul verificat. Cel mai apropiat fragment din pagina oficială:")
        else:
            out["title"] = "Nu am găsit informații despre asta"
            out["facts"].append("Sursele oficiale verificate pentru acest ghid nu menționează acest lucru.")
        out["unconfirmed"] += [u for u in card.get("unconfirmed", [])][:3]
        out["general"] = general_answer(card, None, question)
        return out

    out["title"] = item.get("name") or item["title"]
    out["quotes"] = quote_entries(item)
    out["links"] = [{"label": src(item)["title"], "url": src(item)["url"]}]
    if kind == "doc":
        if want_cost or want_time:
            out["unconfirmed"].append("Sursele oficiale verificate nu precizează costul sau termenul pentru acest document.")
        if wants_content:
            out["facts"].append("Sursa oficială menționează acest document, dar nu detaliază ce trebuie să conțină.")
        elif where_ok[item["id"]] and item.get("where_to_get"):
            out["facts"].append(f"Conform sursei, îl obții: {item['where_to_get']}.")
        else:
            out["facts"].append("Sursa oficială nu precizează de unde sau de la cine se obține acest document.")
            if item.get("hint"):
                out["hint"] = item["hint"]
        step = next((st for st in card["steps"] if st["id"] == item.get("used_in")), None)
        if step:
            out["facts"].append(f"Îl folosești la pasul {step['order'] if 'order' in step else card['steps'].index(step) + 1}: {step['title']}"
                                + (f" ({step['where']})." if step.get("where") else "."))
    else:
        out["facts"].append(item["description"])
        if item.get("where"):
            out["facts"].append(f"Unde: {item['where']}.")
        if want_cost:
            out["facts"].append(f"Cost: {item['cost']}." if item.get("cost") else "Costul acestui pas nu este precizat în sursele verificate.")
            if not item.get("cost"):
                out["unconfirmed"] += [u for u in card.get("unconfirmed", []) if re.search(r"sum|tarif|cost", fold(u))][:2]
        if want_time:
            out["facts"].append(f"Durată: {item['duration']}." if item.get("duration") else "Durata acestui pas nu este precizată în sursele verificate.")
            if not item.get("duration"):
                out["unconfirmed"] += [u for u in card.get("unconfirmed", []) if re.search(r"termen|durat|deadline", fold(u))][:2]

    incomplete = any("nu precizeaz" in fold(f) or "nu este precizat" in fold(f) or "nu detaliaz" in fold(f) for f in out["facts"]) \
        or bool(out["unconfirmed"])
    if wants_content or incomplete:
        st = next((x for x in card["steps"] if x["id"] == item.get("used_in")), None) if kind == "doc" else item
        out["general"] = general_answer(card, item, question, (st or {}).get("where") or "")
        if out["general"]:
            out["hint"] = None  # the generated answer replaces the static suggestion
    return out

@app.get("/api/health")
def health():
    status = provider_status()
    checks = {}
    if GEMINI_API_KEY:
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{GEMINI_BASE_URL}/models", params={"key": GEMINI_API_KEY})
            checks["gemini_ok"] = r.status_code == 200
            if r.status_code != 200:
                checks["gemini_error"] = f"HTTP {r.status_code}"
        except Exception as e:
            checks["gemini_ok"] = False
            checks["gemini_error"] = str(e)
    else:
        checks["gemini_ok"] = False
        checks["gemini_error"] = "GEMINI_API_KEY lipsește"
    if OPENROUTER_API_KEY:
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{OPENROUTER_BASE_URL}/models", headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"})
            checks["openrouter_ok"] = r.status_code == 200
            if r.status_code != 200:
                checks["openrouter_error"] = f"HTTP {r.status_code}"
        except Exception as e:
            checks["openrouter_ok"] = False
            checks["openrouter_error"] = str(e)
    else:
        checks["openrouter_ok"] = False
    if os.getenv("ENABLE_OLLAMA_FALLBACK", "false").strip().lower() == "true":
        try:
            with httpx.Client(timeout=3) as client:
                r = client.get(f"{OLLAMA_URL}/api/tags")
                r.raise_for_status()
                models = [m.get("name") for m in r.json().get("models", [])]
            checks.update({"ollama_ok": True, "ollama_model": OLLAMA_MODEL,
                           "ollama_model_installed": OLLAMA_MODEL in models, "installed_models": models})
        except Exception as e:
            checks.update({"ollama_ok": False, "ollama_model": OLLAMA_MODEL, "ollama_model_installed": False,
                           "ollama_error": str(e)})
    else:
        checks.update({"ollama_ok": False, "ollama_model": OLLAMA_MODEL,
                       "ollama_model_installed": False, "ollama_disabled": True})
    active_ok = bool(checks.get(f"{AI_PROVIDER}_ok")) if AI_PROVIDER not in {"ollama", "none", "disabled"} else bool(checks.get("ollama_ok") and checks.get("ollama_model_installed"))
    fallback_ok = bool(checks.get(f"{AI_FALLBACK_PROVIDER}_ok")) if AI_FALLBACK_PROVIDER not in {"ollama", "none", "disabled", ""} else bool(checks.get("ollama_ok") and checks.get("ollama_model_installed"))
    checks.update({"provider": AI_PROVIDER, "active": llm_label(), "primary_ok": active_ok,
                   "fallback_ok": fallback_ok, "ok": active_ok or fallback_ok,
                   "one_llm_call_per_question": True,
                   "retrieval": "local hybrid + approved official web sources"})
    checks.update(status)
    return checks

@app.post("/api/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Întrebarea este goală.")

    # A short follow-up that refers back ("da ștampila cum o primesc?") is read together with the previous question.
    prev_q = str((req.context or {}).get("prev_question") or "").strip()
    if prev_q and len(question.split()) <= 8 and detect_category(question) == "general" \
            and re.search(r"\b(o|il|le|ii|asta|aceasta|acesta|aceea|atunci|dar|si|da)\b", fold(question)):
        question = f"{prev_q} — {question}"

    # Follow-up about the guide on screen ("de unde iau documentul X?"): answer from that guide.
    ctx_id = (req.context or {}).get("card_id")
    if ctx_id:
        ctx_card = next((c for c in load_cards() if c["id"] == ctx_id), None)
        if ctx_card and is_followup(ctx_card, question):
            return {
                "allowed": True, "needs_clarification": False, "followup": followup_answer(ctx_card, question),
                "category": ctx_card["category"], "profile": req.answers,
                "card": {"id": ctx_card["id"], "title": ctx_card["title"], "last_verified": ctx_card["last_verified"]},
                "sources": [], "source_count": 0, "policy": {"allowed_only": True, "curated_card": True, "followup": True},
            }

    # Domain Guard runs BEFORE web search and BEFORE the answer model.
    domain = get_domain_decision(question)

    if domain["allowed"] is False:
        return {
            "allowed": False,
            "domain_guard": domain,
            "answer": {
                "summary": "🛑 Această întrebare este în afara domeniului DocuGuide.",
                "clarification_needed": False,
                "clarifying_questions": [],
                "documents": [],
                "steps": [],
                "warnings": [
                    "DocuGuide este specializat în documente și proceduri administrative."
                ],
                "contradictions": []
            },
            "category": "other",
            "country": None,
            "search_queries": [],
            "sources": [],
            "source_count": 0,
            "policy": {
                "allowed_only": True,
                "ai_provider": AI_PROVIDER,
                "domain_guard": True,
                "web_search_skipped": True
            }
        }

    category = detect_category(question) if req.category == "auto" else req.category
    country = detect_country(question) if req.country == "auto" else req.country

    # Clarifying-question flow: ask for missing slots BEFORE any search or LLM call.
    slot_card = card_for_slots(category, question)
    profile, missing = missing_slots(category, question, req.answers, req.country,
                                     only=slot_card.get("slots") if slot_card else None)
    if missing and ENABLE_CLARIFICATIONS:
        return {
            "allowed": True,
            "needs_clarification": True,
            "domain_guard": domain,
            "category": category,
            "country": country,
            "profile": profile,
            "questions": [
                {"key": s["key"], "type": s["type"], "ask": s["ask"], "options": s["options"], "no_other": s.get("no_other", False), "placeholder": s.get("placeholder")}
                for s in missing
            ],
        }

    # Curated, quote-verified procedure card first: ordered, confirmed, no LLM needed.
    card = find_card(category, question, profile)
    if card:
        answer, sources, confirmed = card_answer(card, profile)
        return {
            "allowed": True, "needs_clarification": False, "profile": profile, "domain_guard": domain,
            "answer": answer, "category": category, "country": country, "search_queries": [],
            "sources": sources, "source_count": len(sources),
            "card": {"id": card["id"], "title": card["title"], "last_verified": card["last_verified"], "confirmed": confirmed},
            "policy": {"allowed_only": True, "ai_provider": AI_PROVIDER, "curated_card": True},
        }

    results = search_web(question, category, country)
    evidence = evidence_pack(results, question, category)

    if not evidence:
        # Never let the model improvise without official evidence.
        return {
            "allowed": True,
            "needs_clarification": False,
            "profile": profile,
            "domain_guard": domain,
            "answer": {
                "summary": "Nu am găsit surse oficiale verificate pentru această întrebare, deci nu pot construi un ghid de încredere.",
                "clarification_needed": False,
                "clarifying_questions": [],
                "documents": [],
                "steps": [],
                "warnings": [
                    "Nu a fost găsită nicio pagină în domeniile oficiale aprobate. Verifică direct la instituția responsabilă sau reformulează întrebarea."
                ],
                "contradictions": [],
            },
            "category": category,
            "country": country,
            "search_queries": build_queries(question, category, country),
            "sources": [],
            "source_count": 0,
            "policy": {"allowed_only": True, "ai_provider": AI_PROVIDER, "no_evidence": True},
        }

    if not subject_in_sources(question, category, evidence):
        return {
            "allowed": True, "needs_clarification": False, "profile": profile, "domain_guard": domain,
            "answer": {
                "summary": "Nu am găsit nimic despre această temă în sursele oficiale. DocuGuide ajută cu documente și proceduri administrative din Republica Moldova.",
                "clarification_needed": False, "clarifying_questions": [], "documents": [], "steps": [],
                "warnings": ["Reformulează cu situația concretă, de exemplu: «ce acte trebuie ca să deschid un SRL» sau «cum înregistrez o mașină adusă din Germania»."],
                "contradictions": [],
            },
            "category": category, "country": country, "search_queries": build_queries(question, category, country),
            "sources": [], "source_count": 0, "policy": {"allowed_only": True, "ai_provider": AI_PROVIDER, "no_evidence": True},
        }

    if LLM_MAX_PROMPT_CHARS:
        # shrink the evidence evenly so the whole prompt stays within the provider's token budget
        room = max(LLM_MAX_PROMPT_CHARS - 3500, 1200)
        per_source = max(room // max(len(evidence), 1), 500)
        for e in evidence:
            e["text"] = e["text"][:per_source]
    prompt = make_prompt(question, category, country, evidence, profile)

    try:
        answer = call_ai(prompt)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            raise HTTPException(503, "Providerul AI a atins o limită temporară. Încearcă din nou peste puțin timp sau folosește Ollama local.")
        raise HTTPException(503, f"Serviciul AI ({llm_label()}) a returnat HTTP {e.response.status_code}. Verifică /api/health.")
    except Exception as e:
        if not GEMINI_API_KEY and AI_PROVIDER == "gemini":
            raise HTTPException(
                503,
                "Gemini nu este configurat. Deschide fișierul .env și completează GEMINI_API_KEY. "
                "Ollama nu este folosit automat. Verifică apoi /api/health."
            )
        raise HTTPException(503, f"Serviciul AI nu a putut genera răspunsul. Verifică /api/health. Detalii: {e}")
    answer = sanitize_answer(answer, evidence)
    if not answer["documents"] and not answer["steps"]:
        answer["extracts"] = build_extracts(evidence, question, category)
        if answer["extracts"]:
            answer["summary"] = ("Nu am putut construi un ghid structurat și verificat, dar iată fragmentele "
                                 "relevante din sursele oficiale găsite:")

    # Add source metadata for UI. IDs match evidence IDs.
    source_cards = []
    for e in evidence:
        source_cards.append({
            "id": e["id"],
            "title": e["title"],
            "url": e["url"],
            "organization": e["organization"],
            "authority": e["authority"],
            "fetched": e["fetched"],
        })

    return {
        "allowed": True,
        "needs_clarification": False,
        "profile": profile,
        "domain_guard": domain,
        "answer": answer,
        "category": category,
        "country": country,
        "search_queries": build_queries(question, category, country),
        "sources": source_cards,
        "source_count": len(source_cards),
        "policy": {
            "allowed_only": True,
            "ai_provider": AI_PROVIDER,
            "requires_evidence_for_required": True
        }
    }

app.mount("/", StaticFiles(directory=BASE / "frontend" / "dist", html=True), name="frontend")
