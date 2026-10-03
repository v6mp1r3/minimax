import { useEffect, useMemo, useRef, useState } from "react";

const categories = [
  {
    id: "education",
    title: "Educație și studii",
    description: "Erasmus, burse, universitate și echivalarea diplomelor.",
    icon: "🎓",
    color: "mint",
    topics: ["Erasmus", "Înscriere la universitate", "Echivalarea diplomelor", "Burse și finanțare"],
  },
  {
    id: "health",
    title: "Sănătate",
    description: "Înregistrarea la medic, asigurare și acces la servicii.",
    icon: "🩺",
    color: "pink",
    topics: ["Înregistrare la medic", "Asigurare medicală", "Servicii medicale"],
  },
  {
    id: "travel",
    title: "Călătorii și relocare",
    description: "Vize, ședere și documente de călătorie.",
    icon: "✈️",
    color: "blue",
    topics: ["Viză", "Permis de ședere", "Relocare în străinătate"],
  },
  {
    id: "public",
    title: "Acte și servicii publice",
    description: "Buletin, pașaport, stare civilă și servicii publice.",
    icon: "🪪",
    color: "mint",
    topics: ["Buletin", "Pașaport", "Stare civilă", "Alte servicii publice"],
  },
  {
    id: "career",
    title: "Muncă și carieră",
    description: "Angajare, acte de muncă și calificări.",
    icon: "💼",
    color: "orange",
    topics: ["Angajare", "Contract de muncă", "Recunoașterea calificărilor"],
  },
  {
    id: "business",
    title: "Afaceri și finanțe",
    description: "Înregistrare firmă, autorizații și acte fiscale.",
    icon: "🏢",
    color: "purple",
    topics: ["Deschiderea unei firme", "Acte fiscale", "Autorizații"],
  },
  {
    id: "daily",
    title: "Viață cotidiană",
    description: "Închiriere, schimbarea domiciliului și utilități.",
    icon: "🏠",
    color: "blue",
    topics: ["Închiriere", "Schimbarea domiciliului", "Utilități"],
  },
];

// The backend classifies each question; map its category to the ones shown in the UI.
const backendCategory = {
  education: "education",
  health: "health",
  relocation: "travel",
  auto: "public",
  rent: "daily",
  employment: "career",
  business: "business",
};
const categoryById = (id) => categories.find((c) => c.id === id) || null;

const HISTORY_KEY = "docuguide.history";
const loadHistory = () => {
  try {
    const list = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
};
const MAX_HISTORY = 20;
// pinned conversations first (in their current order), then the most recent others
const orderHistory = (list) => [...list.filter((h) => h.pinned), ...list.filter((h) => !h.pinned)];
const saveHistory = (list) => {
  const ordered = orderHistory(list);
  const pinned = ordered.filter((h) => h.pinned);
  const rest = ordered.filter((h) => !h.pinned).slice(0, Math.max(MAX_HISTORY - pinned.length, 5));
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify([...pinned, ...rest]));
  } catch {
    /* storage unavailable: history is just not kept */
  }
};

const examples = [
  "Vreau să plec cu Erasmus în Franța",
  "Cum mă înregistrez la medic?",
  "Mi-am pierdut buletinul",
];

function Logo({ onClick }) {
  return (
    <button className="logo" onClick={onClick} aria-label="DocuGuide - Acasă">
      <span className="logo-icon">♧</span>
      <span>DocuGuide</span>
    </button>
  );
}

function Navbar({ onHome, onChat }) {
  return (
    <header className="navbar">
      <Logo onClick={onHome} />

      <div className="navbar-actions">
        <button className="language-button">RO</button>
        <button className="primary-button" onClick={onChat}>
          Deschide Chat
        </button>
      </div>
    </header>
  );
}

function HomePage({ onChat, onCategory }) {
  const [question, setQuestion] = useState("");

  const sendQuestion = () => {
    if (question.trim()) {
      onChat(question);
    }
  };

  return (
    <>
      <section className="hero">
        <div className="hero-decoration decoration-one">
          <span>✦</span>
          <div />
          <div />
        </div>

        <div className="hero-decoration decoration-two">
          <span>✦</span>
          <div />
          <div />
        </div>

        <div className="hero-content">
          <div className="hero-label">
            <span>✦</span> Asistent AI pentru documente
          </div>

          <h1>
            Orice situație. <span>Un singur ghid.</span>
          </h1>

          <p className="hero-description">
            Obține rapid informații despre documentele necesare,
            pașii de urmat și procedurile oficiale, pentru orice situație.
          </p>

          <div className="search-box">
            <span className="search-icon">⌕</span>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendQuestion()}
              placeholder="Scrie ce vrei să faci..."
              aria-label="Descrie situația ta"
            />
            <button
              className="search-submit"
              onClick={sendQuestion}
              aria-label="Trimite întrebarea"
            >
              →
            </button>
          </div>

          <div className="examples">
            <span>Exemple:</span>
            {examples.map((example) => (
              <button
                key={example}
                className="example-chip"
                onClick={() => {
                  setQuestion(example);
                  onChat(example);
                }}
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="categories-section" id="categorii">
        <h2>Explorează categoriile principale</h2>

        <div className="category-grid">
          {categories.map((category) => (
            <button
              className="category-card"
              key={category.id}
              onClick={() => onCategory(category)}
            >
              <span className={`category-icon ${category.color}`}>
                {category.icon}
              </span>

              <span className="category-text">
                <strong>{category.title}</strong>
                <small>{category.description}</small>
              </span>

              <span className="category-arrow">→</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function CategoryPage({ category, onChat, onHome }) {
  const [activeTopic, setActiveTopic] = useState("Toate");

  if (!category) return null;

  const topics = ["Toate", ...category.topics];
  const visibleTopics =
    activeTopic === "Toate"
      ? category.topics
      : [activeTopic];

  return (
    <main className="category-page">
      <section className="category-banner">
        <span className={`category-icon large ${category.color}`}>
          {category.icon}
        </span>
        <div>
          <h1>{category.title}</h1>
          <p>{category.description}</p>
        </div>
      </section>

      <div className="topic-filters">
        {topics.map((topic) => (
          <button
            key={topic}
            className={`filter-chip ${activeTopic === topic ? "active" : ""}`}
            onClick={() => setActiveTopic(topic)}
          >
            {topic}
          </button>
        ))}
      </div>

      <div className="topic-grid">
        {visibleTopics.map((topic, index) => (
          <article className="topic-card" key={topic}>
            <div className={`topic-illustration illustration-${index % 4}`}>
              <div className="document-illustration">
                <span />
                <span />
              </div>
            </div>

            <div className="topic-card-content">
              <h3>{topic}</h3>
              <p>
                Află ce documente sunt necesare și care sunt pașii de urmat.
              </p>
              <button onClick={() => onChat(`Vreau informații despre: ${topic}`)}>
                Vezi pașii <span>→</span>
              </button>
            </div>
          </article>
        ))}
      </div>

      <section className="category-cta">
        <div>
          <strong>Nu știi de unde să începi?</strong>
          <p>Descrie situația ta și primești un ghid adaptat.</p>
        </div>
        <button className="primary-button" onClick={() => onChat("")}>
          Întreabă DocuGuide <span>→</span>
        </button>
      </section>

      <button className="back-link" onClick={onHome}>
        ← Înapoi la pagina principală
      </button>
    </main>
  );
}

const STATUS_LABEL = {
  required: "Obligatoriu",
  possible: "Posibil",
  recommended: "Recomandat",
  unknown: "Neconfirmat",
};

function SourceRefs({ ids = [], sources }) {
  const byId = Object.fromEntries(sources.map((s) => [s.id, s]));
  return ids.map((id) =>
    byId[id] ? (
      <a
        key={id}
        className="source-ref"
        href={byId[id].url}
        target="_blank"
        rel="noreferrer"
        title={byId[id].title}
      >
        {id}
      </a>
    ) : null
  );
}

const CHECKS_KEY = "docuguide.checks";
const loadChecks = () => {
  try {
    return JSON.parse(localStorage.getItem(CHECKS_KEY) || "{}") || {};
  } catch {
    return {};
  }
};

// Verbatim official quote(s) + link, hidden until asked for
function SourceToggle({ quotes = [], url }) {
  const list = quotes.filter(Boolean);
  if (!list.length) return null;
  return (
    <details className="source-toggle">
      <summary>Vezi sursa</summary>
      {list.map((q, i) => (
        <blockquote className="source-quote" key={i}>
          „{q}”
        </blockquote>
      ))}
      {url && (
        <a href={url} target="_blank" rel="noreferrer">
          Deschide pagina oficială
        </a>
      )}
    </details>
  );
}

function AnswerCard({ data }) {
  const { answer, sources = [], card } = data;
  const documents = answer.documents || [];
  const steps = answer.steps || [];
  const warnings = answer.warnings || [];
  const contradictions = answer.contradictions || [];
  const byId = Object.fromEntries(sources.map((s) => [s.id, s]));

  // "Neconfirmat în surse: …" items are collapsed; notes that change what you do stay visible
  const UNCONFIRMED = /^Neconfirmat în surse:\s*/;
  const unconfirmed = warnings.filter((w) => UNCONFIRMED.test(w)).map((w) => w.replace(UNCONFIRMED, ""));
  const visibleWarnings = warnings.filter((w) => !UNCONFIRMED.test(w));

  // document checklist, remembered in this browser
  const guideKey = card?.id || `ad-hoc:${(answer.summary || "").slice(0, 40)}`;
  const [checks, setChecks] = useState(loadChecks);
  const isChecked = (name) => !!checks[`${guideKey}:${name}`];
  const toggleCheck = (name) => {
    const next = { ...checks, [`${guideKey}:${name}`]: !isChecked(name) };
    setChecks(next);
    try {
      localStorage.setItem(CHECKS_KEY, JSON.stringify(next));
    } catch {
      /* storage unavailable: the ticks just are not remembered */
    }
  };
  const done = documents.filter((d) => isChecked(d.name)).length;

  return (
    <div className="answer-card">
      <p className="answer-summary">{answer.summary}</p>

      {visibleWarnings.length > 0 && (
        <ul className="answer-warnings">
          {visibleWarnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      {steps.length > 0 && (
        <section>
          <h4>Pași de urmat</h4>
          <ol className="step-list">
            {steps.map((s, i) => (
              <li key={i}>
                <div className="doc-head">
                  <strong>{s.title}</strong>
                  {s.check === "confirmed" && <span className="tick" title="Confirmat acum pe pagina oficială">✓</span>}
                  {s.check && s.check !== "confirmed" && (
                    <span className="badge unknown">
                      {s.check === "changed" ? "Pagină schimbată" : "Neverificat acum"}
                    </span>
                  )}
                  <SourceRefs ids={s.sources} sources={sources} />
                </div>
                {s.description && <p>{s.description}</p>}
                {(s.where || s.cost || s.duration || s.depends_on_step) && (
                  <div className="chips">
                    {s.where && <span className="chip">📍 {s.where}</span>}
                    {s.cost && <span className="chip">💰 {s.cost}</span>}
                    {s.duration && <span className="chip">⏱ {s.duration}</span>}
                    {s.depends_on_step && <span className="chip">după pasul {s.depends_on_step}</span>}
                  </div>
                )}
                <SourceToggle quotes={s.quotes || (s.quote ? [s.quote] : [])} url={s.link} />
              </li>
            ))}
          </ol>
        </section>
      )}

      {documents.length > 0 && (
        <section>
          <h4>
            Documente <span className="progress">{done}/{documents.length} pregătite</span>
          </h4>
          <ul className="doc-list check-list">
            {documents.map((d, i) => (
              <li key={i} className={isChecked(d.name) ? "done" : ""}>
                <label className="doc-head">
                  <input type="checkbox" checked={isChecked(d.name)} onChange={() => toggleCheck(d.name)} />
                  <strong>{d.name}</strong>
                  <span className={`badge ${d.status}`}>{STATUS_LABEL[d.status]}</span>
                  {d.check === "confirmed" && <span className="tick" title="Confirmat acum pe pagina oficială">✓</span>}
                  <SourceRefs ids={d.sources} sources={sources} />
                </label>
                {d.reason && d.check !== "confirmed" && <p>{d.reason}</p>}
                {d.where_to_get && <p className="meta">Unde: {d.where_to_get}</p>}
                <SourceToggle quotes={d.quote ? [d.quote] : []} url={byId[(d.sources || [])[0]]?.url} />
              </li>
            ))}
          </ul>
        </section>
      )}

      {(answer.extracts || []).length > 0 && (
        <section>
          <h4>Fragmente din sursele oficiale</h4>
          {answer.extracts.map((e, i) => (
            <blockquote className="source-quote" key={i}>
              {e.text}
              <a href={e.url} target="_blank" rel="noreferrer">
                [{e.id}] {e.source}
              </a>
            </blockquote>
          ))}
        </section>
      )}

      {contradictions.length > 0 && (
        <section>
          <h4>Surse care se contrazic</h4>
          <ul className="answer-warnings">
            {contradictions.map((c, i) => (
              <li key={i}>
                <strong>{c.topic}:</strong> {c.description}
              </li>
            ))}
          </ul>
        </section>
      )}

      {unconfirmed.length > 0 && (
        <details className="unconfirmed-box">
          <summary>Ce nu este confirmat în surse ({unconfirmed.length})</summary>
          <ul>
            {unconfirmed.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </details>
      )}

      {sources.length > 0 && (
        <section>
          <h4>Surse oficiale</h4>
          <ul className="source-list">
            {sources.map((s) => (
              <li key={s.id}>
                <span className="source-ref">{s.id}</span>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.organization} – {s.title}
                </a>
              </li>
            ))}
          </ul>
        </section>
      )}

      {card && (
        <p className="meta">
          Ghid verificat ({card.confirmed} elemente confirmate acum). Ultima verificare
          manuală: {card.last_verified}.
        </p>
      )}
    </div>
  );
}

function FollowupCard({ data }) {
  const { title, facts = [], quotes = [], hint, unconfirmed = [], links = [], general } = data;
  return (
    <div className="answer-card">
      <h4 className="followup-title">{title}</h4>
      {facts.map((f, i) => (
        <p key={i}>{f}</p>
      ))}
      {quotes.map((q, i) => (
        <blockquote className="source-quote" key={i}>
          „{q.text}”
          <a href={q.url} target="_blank" rel="noreferrer">
            {q.source}
          </a>
        </blockquote>
      ))}
      {general && (
        <div className="general-answer">
          <strong>Răspuns orientativ — generat de AI, nu provine dintr-o sursă oficială</strong>
          <div className="general-text">{general}</div>
          <small>Verifică la instituția responsabilă înainte să te bazezi pe el.</small>
        </div>
      )}
      {hint && (
        <p className="hint-unconfirmed">
          <strong>Sugestie (neconfirmată în sursele oficiale):</strong> {hint}
        </p>
      )}
      {unconfirmed.length > 0 && (
        <ul className="answer-warnings">
          {unconfirmed.map((u, i) => (
            <li key={i}>{u}</li>
          ))}
        </ul>
      )}
      {links.map((l, i) => (
        <a className="step-link" key={i} href={l.url} target="_blank" rel="noreferrer">
          Deschide pagina oficială
        </a>
      ))}
    </div>
  );
}

function QuestionCard({ q, active, onSubmit }) {
  const options = (q.options || []).map((o) =>
    typeof o === "string" ? { value: o, label: o } : { ...o, label: o.label || o.value }
  );
  const isMulti = q.type === "multi";
  const [picked, setPicked] = useState([]);
  const [other, setOther] = useState("");

  const toggle = (value) =>
    setPicked((old) => (old.includes(value) ? old.filter((v) => v !== value) : [...old, value]));

  const labelOf = (value) => options.find((o) => o.value === value)?.label || value;

  const submitMulti = () => {
    const values = other.trim() ? [...picked, `other: ${other.trim()}`] : picked;
    if (values.length) onSubmit(values, values.map(labelOf).join(", "));
  };

  const submitOther = () => {
    const text = other.trim();
    if (text) onSubmit(`other: ${text}`, text);
  };

  return (
    <div className="assistant-bubble question-bubble">
      <strong>{q.ask}</strong>
      {isMulti && <p>Poți alege mai multe variante.</p>}

      <div className="answer-options">
        {options.map((o) => (
          <button
            key={o.value}
            disabled={!active}
            className={picked.includes(o.value) ? "selected" : ""}
            onClick={() => (isMulti ? toggle(o.value) : onSubmit(o.value, o.label))}
          >
            {o.label}
            <span>{isMulti ? (picked.includes(o.value) ? "✓" : "+") : "›"}</span>
          </button>
        ))}

        {!q.no_other && active && (
          <div className="other-row">
            <input
              value={other}
              onChange={(e) => setOther(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isMulti && submitOther()}
              placeholder={q.placeholder || "Altă variantă..."}
              aria-label="Altă variantă"
            />
            {!isMulti && (
              <button onClick={submitOther} disabled={!other.trim()}>
                Trimite
              </button>
            )}
          </div>
        )}
      </div>

      {isMulti && active && (
        <button
          className="primary-button multi-continue"
          onClick={submitMulti}
          disabled={!picked.length && !other.trim()}
        >
          Continuă
        </button>
      )}
    </div>
  );
}

function ChatPage({ initialMessage, onHome }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null); // { question, answers } while clarifying
  const [conversation, setConversation] = useState(
    initialMessage ? [{ role: "user", type: "text", text: initialMessage }] : []
  );
  const started = useRef(false);
  const lastQuestion = useRef(""); // previous question, so a short follow-up can refer back to it
  const endRef = useRef(null);
  const [chatId, setChatId] = useState(() => String(Date.now()));
  const [categoryId, setCategoryId] = useState(null);

  const push = (...items) => setConversation((old) => [...old, ...items]);

  const currentCardId = () =>
    [...conversation].reverse().map((m) => m.data?.card?.id).find(Boolean) || null;

  const ask = async (question, answers = {}, prev = lastQuestion.current) => {
    if (Object.keys(answers).length === 0) lastQuestion.current = question;
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          category: "auto",
          country: "auto",
          answers,
          // the guide on screen, so "de unde iau documentul X?" is answered from it
          context: {
            card_id: Object.keys(answers).length === 0 ? currentCardId() : null,
            prev_question: prev,
          },
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Serverul a răspuns cu eroarea ${res.status}.`);
      }
      const data = await res.json();

      const detected = backendCategory[data.category];
      if (detected) setCategoryId(detected);

      if (data.followup) {
        setPending(null);
        push({ role: "assistant", type: "followup", data });
      } else if (data.needs_clarification && data.questions?.length) {
        setPending({ question, answers, prev });
        const items = [];
        if (Object.keys(answers).length === 0) {
          items.push({
            role: "assistant",
            type: "text",
            text: "Pentru a-ți pregăti un ghid personalizat, am nevoie de câteva detalii:",
          });
        }
        items.push({ role: "assistant", type: "question", q: data.questions[0] });
        push(...items);
      } else {
        setPending(null);
        push({ role: "assistant", type: "answer", data });
      }
    } catch (e) {
      setPending(null);
      let text = e.message;
      if (e instanceof TypeError) {
        text = "Nu mă pot conecta la server. Pornește backend-ul (run.bat / run.sh) și încearcă din nou.";
      } else if (/10061|refused|ConnectError|timed out|Ollama/i.test(text)) {
        text =
          "Serviciul AI nu răspunde. Verifică cheia GROQ_API_KEY din fișierul .env, sau pornește Ollama " +
          "(`ollama serve`, modelul: `ollama pull llama3.2:3b`). Detalii: " + text;
      }
      push({ role: "assistant", type: "text", text });
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (initialMessage && !started.current) {
      started.current = true;
      ask(initialMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // History = this conversation (kept up to date) + the ones saved earlier in this browser.
  const [historyRev, setHistoryRev] = useState(0); // bumped after pin / delete so the list is re-read
  const history = useMemo(() => {
    const firstUser = conversation.find((m) => m.role === "user");
    const all = loadHistory();
    const saved = all.filter((h) => h.id !== chatId);
    if (!firstUser) return orderHistory(saved);
    const pinned = !!all.find((h) => h.id === chatId)?.pinned;
    return orderHistory([
      { id: chatId, title: firstUser.text.slice(0, 48), categoryId, conversation, pinned },
      ...saved,
    ]).slice(0, MAX_HISTORY + 10);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation, categoryId, chatId, historyRev]);

  useEffect(() => {
    if (conversation.length) saveHistory(history);
  }, [history, conversation.length]);

  const togglePin = (id) => {
    saveHistory(history.map((h) => (h.id === id ? { ...h, pinned: !h.pinned } : h)));
    setHistoryRev((r) => r + 1);
  };

  const deleteChat = (id) => {
    if (!window.confirm("Ștergi această conversație?")) return;
    saveHistory(history.filter((h) => h.id !== id));
    if (id === chatId) {
      newChat(); // the open conversation is gone: start a clean one so it is not saved again
    }
    setHistoryRev((r) => r + 1);
  };

  const openHistory = (item) => {
    if (busy) return;
    // an unanswered clarification question cannot be resumed: drop it
    const conv = [...item.conversation];
    while (conv.length && conv[conv.length - 1].type === "question") conv.pop();
    setChatId(item.id);
    setCategoryId(item.categoryId);
    setConversation(conv);
    setPending(null);
    setMessage("");
  };

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation, busy]);

  const sendMessage = (text) => {
    if (busy || !text.trim()) return;
    push({ role: "user", type: "text", text });
    setMessage("");
    setPending(null);
    ask(text);
  };

  const answerQuestion = (q, value, label) => {
    if (busy || !pending) return;
    push({ role: "user", type: "text", text: label });
    ask(pending.question, { ...pending.answers, [q.key]: value }, pending.prev);
  };

  const newChat = () => {
    lastQuestion.current = "";
    setChatId(String(Date.now()));
    setCategoryId(null);
    setConversation([]);
    setPending(null);
    setMessage("");
  };

  const lastIndex = conversation.length - 1;

  return (
    <main className="chat-layout">
      <aside className="chat-sidebar">
        <Logo onClick={onHome} />

        <button className="new-chat-button" onClick={newChat}>
          + Conversație nouă
        </button>

        <button className="all-conversations">Toate conversațiile</button>

        <nav className="sidebar-categories">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => sendMessage(`Vreau informații despre ${category.title}`)}
            >
              <span className="side-icon">{category.icon}</span>
              {category.title}
            </button>
          ))}
        </nav>

        <div className="recent-conversations">
          <strong>Conversații recente</strong>
          {history.length === 0 && <small className="recent-empty">Încă nu ai conversații.</small>}
          {history.map((item) => {
            const c = categoryById(item.categoryId);
            return (
              <div
                key={item.id}
                className={`recent-item ${item.id === chatId ? "active" : ""} ${item.pinned ? "pinned" : ""}`}
              >
                <button
                  className="recent-open"
                  onClick={() => openHistory(item)}
                  title={c ? c.title : "Conversație"}
                >
                  <span className="side-icon">{c ? c.icon : "💬"}</span>
                  <span className="recent-title">{item.title}</span>
                  {item.pinned && <span className="pin-mark" aria-label="Fixată">📌</span>}
                </button>
                <div className="recent-actions">
                  <button
                    className="icon-action"
                    onClick={() => togglePin(item.id)}
                    title={item.pinned ? "Anulează fixarea" : "Fixează în partea de sus"}
                    aria-label={item.pinned ? "Anulează fixarea" : "Fixează conversația"}
                  >
                    {item.pinned ? "📍" : "📌"}
                  </button>
                  <button
                    className="icon-action"
                    onClick={() => deleteChat(item.id)}
                    title="Șterge conversația"
                    aria-label="Șterge conversația"
                  >
                    🗑
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <strong>Asistent DocuGuide</strong>
          {categoryById(categoryId) && (
            <span className="chat-category">
              {categoryById(categoryId).icon} {categoryById(categoryId).title}
            </span>
          )}
          <button className="mobile-home" onClick={onHome}>Acasă</button>
        </header>

        <div className="chat-messages">
          {conversation.length === 0 && (
            <div className="chat-welcome">
              <span className="chat-avatar">♧</span>
              <div className="assistant-bubble">
                Bună! Sunt asistentul DocuGuide. Spune-mi ce documente
                sau procedură te interesează.
              </div>
            </div>
          )}

          {conversation.map((item, index) => (
            <div
              className={`message-row ${item.role === "user" ? "user-row" : ""}`}
              key={index}
            >
              {item.role === "assistant" && <span className="chat-avatar">♧</span>}

              {item.type === "question" ? (
                <QuestionCard
                  q={item.q}
                  active={index === lastIndex && !busy}
                  onSubmit={(value, label) => answerQuestion(item.q, value, label)}
                />
              ) : item.type === "followup" ? (
                <div className="assistant-bubble answer-bubble">
                  <FollowupCard data={item.data.followup} />
                </div>
              ) : item.type === "answer" ? (
                <div className="assistant-bubble answer-bubble">
                  <AnswerCard data={item.data} />
                </div>
              ) : (
                <div className={item.role === "user" ? "user-bubble" : "assistant-bubble"}>
                  {item.text}
                </div>
              )}
            </div>
          ))}

          {busy && (
            <div className="message-row">
              <span className="chat-avatar">♧</span>
              <div className="assistant-bubble typing" role="status">
                Caut în sursele oficiale<span>.</span><span>.</span><span>.</span>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          className="chat-input-area"
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(message);
          }}
        >
          <button type="button" className="add-button" aria-label="Adaugă">
            +
          </button>
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Scrie un mesaj..."
            aria-label="Scrie un mesaj"
            disabled={busy}
          />
          <button type="submit" className="chat-send" aria-label="Trimite" disabled={busy}>
            ↑
          </button>
        </form>
      </section>
    </main>
  );
}

function App() {
  const [page, setPage] = useState("home");
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [initialMessage, setInitialMessage] = useState("");

  const openChat = (text = "") => {
    setInitialMessage(text);
    setPage("chat");
  };

  const openCategory = (category) => {
    setSelectedCategory(category);
    setPage("category");
  };

  const goHome = () => setPage("home");

  return (
    <div className="app">
      {page !== "chat" && (
        <Navbar onHome={goHome} onChat={() => openChat("")} />
      )}

      {page === "home" && (
        <HomePage onChat={openChat} onCategory={openCategory} />
      )}

      {page === "category" && (
        <CategoryPage
          category={selectedCategory}
          onChat={openChat}
          onHome={goHome}
        />
      )}

      {page === "chat" && (
        <ChatPage
          key={initialMessage}
          initialMessage={initialMessage}
          onHome={goHome}
        />
      )}
    </div>
  );
}

export default App;
