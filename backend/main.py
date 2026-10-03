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
CACHE_TTL = 30 * 60
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

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

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
    if any(x in q for x in ["firmă", "firma", "companie", "societate", "deschid o firmă", "deschid o firma"]):
        return "business"
    if any(x in q for x in ["medic", "spital", "servicii medicale", "asigurare medicală", "asigurare medicala"]):
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
        r"\bc#\b", r"\blua\b", r"\broblox\b",
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
        r"\bfirmă\b", r"\bfirma\b", r"\bcompanie\b", r"\bautoriza",
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

    if any(re.search(p, q) for p in admin_patterns):
        return {"allowed": True, "reason": "", "category": "administrative"}

    # Ask a tiny local classification call only for ambiguous questions.
    # This keeps the deterministic guard fast while allowing natural questions
    # such as "Vreau să plec la facultate în Germania, ce fac?"
    return {"allowed": "ambiguous", "reason": "", "category": "unknown"}


def llm_domain_guard(question: str):
    prompt = f"""
Classify the user's question for DocuGuide.

DocuGuide ONLY handles:
- documents and administrative procedures
- education / Erasmus / university administration
- public services and identity documents
- visas, residence, relocation and travel documentation
- renting / housing paperwork
- employment paperwork
- opening a company / permits
- administrative health-service access
- vehicle import, customs, registration and car paperwork

Return ONLY JSON:
{{"allowed": true_or_false, "category": "education|public_services|relocation|rent|auto|employment|business|health|other", "reason": "short Romanian reason"}}

User question:
{question}
""".strip()

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": "Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "options": {"temperature": 0}
        }
        with httpx.Client(timeout=45) as client:
            r = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "{}")
        result = json.loads(content)
        return {
            "allowed": bool(result.get("allowed", False)),
            "category": result.get("category", "other"),
            "reason": result.get("reason", "")
        }
    except Exception:
        # Fail closed for ambiguous requests: do not turn DocuGuide into
        # a general-purpose chatbot.
        return {
            "allowed": False,
            "category": "other",
            "reason": "Nu am putut confirma că întrebarea aparține domeniului DocuGuide."
        }


def get_domain_decision(question: str):
    decision = domain_guard(question)
    if decision["allowed"] in (True, False):
        return decision
    return llm_domain_guard(question)


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
            f"acces servicii medicale documente {country}",
            f"asigurare medicală acte {country}",
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
    "health": ["medic", "asigurar", "cnam"],
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
    """Search one approved domain with a site: filter. Returns raw ddgs hits."""
    hits = []
    try:
        with DDGS(timeout=10) as ddgs:
            for query in queries:
                try:
                    for r in ddgs.text(f"site:{domain} {query}", max_results=4):
                        hits.append(r)
                except Exception:
                    continue
    except Exception:
        pass
    return hits

def search_web(question: str, category: str, country: str):
    """Search ONLY the approved domains (site: filter, in parallel).
    No curated/demo fallback: if nothing official is found we return [] and the
    caller reports that honestly instead of letting the model improvise."""
    cache_key = ("search", question, category, country)
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    allowed = allowed_sources(category)
    queries = build_queries(question, category, country)[:2]
    with ThreadPoolExecutor(max_workers=max(1, len(allowed))) as pool:
        per_domain = list(pool.map(lambda d: _site_search(d["domain"], queries), allowed))

    results, seen = [], set()
    for hits in per_domain:
        for r in hits:
            url = r.get("href") or r.get("url") or ""
            if not url or url in seen or not domain_allowed(url, allowed):
                continue
            seen.add(url)
            authority, label = authority_for(url, allowed)
            results.append({
                "title": clean_text(r.get("title", "")),
                "url": url,
                "snippet": clean_text(r.get("body", "")),
                "authority": authority,
                "organization": label,
            })
    stems = stems_for(question, category)
    for r in results:
        r["relevance"] = relevance(f"{r['title']} {r['url']} {r['snippet']}", stems)
    results.sort(key=lambda x: (-x["relevance"], -x["authority"]))
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
    cached = cache_get(("page", url))
    if cached is not None:
        return cached
    try:
        headers = {"User-Agent": "DocuGuide-Hackathon/0.1"}
        with httpx.Client(timeout=8, follow_redirects=True, headers=headers) as client:
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
Clarifying questions were already asked in the UI. Always set "clarification_needed" to false.

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

def call_ollama(prompt):
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "format": "json",
        "messages": [
            {"role": "system", "content": "Return valid JSON only. Answer in Romanian."},
            {"role": "user", "content": prompt},
        ],
        "options": {"temperature": 0.05, "num_ctx": 6000}
    }
    with httpx.Client(timeout=180) as client:
        r = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        r.raise_for_status()
        data = r.json()
    content = data.get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "summary": content,
            "clarification_needed": False,
            "clarifying_questions": [],
            "documents": [],
            "steps": [],
            "warnings": ["Modelul nu a returnat JSON perfect; răspunsul a fost păstrat ca text."],
            "contradictions": []
        }

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
    Returns ({item_id: 'confirmed'|'changed'|'unreachable'}, {source_key: page_ok})."""
    urls = {k: v["url"] for k, v in card["sources"].items()}
    with ThreadPoolExecutor(max_workers=max(1, len(urls))) as pool:
        texts = dict(zip(urls, pool.map(lambda u: _norm(fetch_page(u)[1]), urls.values())))
    status = {}
    for item in card["documents"] + card["steps"]:
        text = texts.get(item["source"], "")
        quotes = [item["quote"]] if "quote" in item else item["quotes"]
        if not text:
            status[item["id"]] = "unreachable"
        elif all(_norm(q) in text for q in quotes):
            status[item["id"]] = "confirmed"
        else:
            status[item["id"]] = "changed"
    return status, {k: bool(t) for k, t in texts.items()}

def card_answer(card: dict, profile: dict | None = None):
    status, page_ok = verify_card(card)
    keys = list(card["sources"])
    sid = {k: i + 1 for i, k in enumerate(keys)}
    label = {"confirmed": "Confirmat acum pe pagina oficială", "changed": "Pagina oficială s-a schimbat — verifică manual",
             "unreachable": "Nu am putut deschide pagina oficială acum; ultima verificare: " + card["last_verified"]}
    docs = [{
        "name": d["name"], "status": d["status"] if status[d["id"]] != "changed" else "unknown",
        "reason": label[status[d["id"]]], "where_to_get": d.get("where_to_get"),
        "sources": [sid[d["source"]]], "quote": d["quote"], "check": status[d["id"]],
    } for d in card["documents"]]
    steps = [{
        "title": st["title"], "description": st["description"], "where": st.get("where"),
        "cost": st.get("cost"), "duration": st.get("duration"), "depends_on_step": st.get("depends_on_step"),
        "link": card["sources"][st["source"]]["url"], "sources": [sid[st["source"]]],
        "quote": st["quotes"][0], "check": status[st["id"]],
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

@app.get("/api/health")
def health():
    try:
        with httpx.Client(timeout=3) as client:
            r = client.get(f"{OLLAMA_URL}/api/tags")
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
        return {
            "ok": True,
            "ai": "ollama",
            "model": OLLAMA_MODEL,
            "model_installed": OLLAMA_MODEL in models,
            "installed_models": models
        }
    except Exception as e:
        return {"ok": False, "ai": "ollama", "model": OLLAMA_MODEL, "error": str(e)}

@app.post("/api/chat")
def chat(req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Întrebarea este goală.")

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
                "local_ai": True,
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
    if missing:
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
            "policy": {"allowed_only": True, "local_ai": True, "curated_card": True},
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
            "policy": {"allowed_only": True, "local_ai": True, "no_evidence": True},
        }

    prompt = make_prompt(question, category, country, evidence, profile)

    try:
        answer = call_ollama(prompt)
    except Exception as e:
        raise HTTPException(503, f"Ollama nu a putut genera răspunsul: {e}")
    answer = sanitize_answer(answer, evidence)

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
            "local_ai": True,
            "requires_evidence_for_required": True
        }
    }

app.mount("/", StaticFiles(directory=BASE / "frontend", html=True), name="frontend")
