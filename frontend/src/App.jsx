import { useEffect, useRef, useState } from "react";

const categories = [
  {
    id: "education",
    title: "Educație și studii",
    description: "Erasmus, burse, universitate și echivalarea diplomelor.",
    icon: "♧",
    color: "mint",
    topics: ["Erasmus", "Înscriere la universitate", "Echivalarea diplomelor", "Burse și finanțare"],
  },
  {
    id: "health",
    title: "Sănătate",
    description: "Înregistrarea la medic, asigurare și acces la servicii.",
    icon: "♡",
    color: "pink",
    topics: ["Înregistrare la medic", "Asigurare medicală", "Servicii medicale"],
  },
  {
    id: "travel",
    title: "Călătorii și relocare",
    description: "Vize, ședere și documente de călătorie.",
    icon: "➤",
    color: "blue",
    topics: ["Viză", "Permis de ședere", "Relocare în străinătate"],
  },
  {
    id: "public",
    title: "Acte și servicii publice",
    description: "Buletin, pașaport, stare civilă și servicii publice.",
    icon: "▤",
    color: "mint",
    topics: ["Buletin", "Pașaport", "Stare civilă", "Alte servicii publice"],
  },
  {
    id: "career",
    title: "Muncă și carieră",
    description: "Angajare, acte de muncă și calificări.",
    icon: "▣",
    color: "orange",
    topics: ["Angajare", "Contract de muncă", "Recunoașterea calificărilor"],
  },
  {
    id: "business",
    title: "Afaceri și finanțe",
    description: "Înregistrare firmă, autorizații și acte fiscale.",
    icon: "⌁",
    color: "purple",
    topics: ["Deschiderea unei firme", "Acte fiscale", "Autorizații"],
  },
];

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

const SpeechRecognitionAPI =
  typeof window !== "undefined" &&
  (window.SpeechRecognition || window.webkitSpeechRecognition);

const SPEECH_ERRORS = {
  "not-allowed": "Permite accesul la microfon în browser ca să poți vorbi.",
  "service-not-allowed": "Permite accesul la microfon în browser ca să poți vorbi.",
  "no-speech": "Nu am auzit nimic. Încearcă din nou.",
  "audio-capture": "Nu găsesc niciun microfon.",
  network: "Recunoașterea vocală are nevoie de conexiune la internet.",
};

function useSpeech(onText) {
  const recRef = useRef(null);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => () => recRef.current?.abort(), []);

  const start = () => {
    const rec = new SpeechRecognitionAPI();
    rec.lang = "ro-RO";
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e) =>
      onText(Array.from(e.results).map((r) => r[0].transcript).join(""));
    rec.onerror = (e) =>
      setError(SPEECH_ERRORS[e.error] || "Recunoașterea vocală a eșuat.");
    rec.onend = () => setListening(false);
    recRef.current = rec;
    setError("");
    setListening(true);
    rec.start();
  };

  return {
    supported: Boolean(SpeechRecognitionAPI),
    listening,
    error,
    toggle: () => (listening ? recRef.current?.stop() : start()),
    cancel: () => recRef.current?.abort(),
  };
}

function MicButton({ voice, disabled }) {
  if (!voice.supported) return null;
  return (
    <button
      type="button"
      className={`mic-button ${voice.listening ? "listening" : ""}`}
      onClick={voice.toggle}
      disabled={disabled}
      aria-pressed={voice.listening}
      aria-label={voice.listening ? "Oprește înregistrarea" : "Spune întrebarea cu vocea"}
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <rect x="9" y="3" width="6" height="12" rx="3" />
        <path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
      </svg>
    </button>
  );
}

function HomePage({ onChat, onCategory }) {
  const [question, setQuestion] = useState("");
  const voice = useSpeech(setQuestion);

  const sendQuestion = () => {
    if (question.trim()) {
      voice.cancel();
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
              placeholder={voice.listening ? "Te ascult..." : "Scrie ce vrei să faci..."}
              aria-label="Descrie situația ta"
            />
            <MicButton voice={voice} />
            <button
              className="search-submit"
              onClick={sendQuestion}
              aria-label="Trimite întrebarea"
            >
              →
            </button>
          </div>
          {voice.error && <p className="voice-error">{voice.error}</p>}

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

function AnswerCard({ data }) {
  const { answer, sources = [], card } = data;
  const documents = answer.documents || [];
  const steps = answer.steps || [];
  const warnings = answer.warnings || [];
  const contradictions = answer.contradictions || [];

  return (
    <div className="answer-card">
      <p className="answer-summary">{answer.summary}</p>

      {warnings.length > 0 && (
        <ul className="answer-warnings">
          {warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}

      {documents.length > 0 && (
        <section>
          <h4>Documente</h4>
          <ul className="doc-list">
            {documents.map((d, i) => (
              <li key={i}>
                <div className="doc-head">
                  <strong>{d.name}</strong>
                  <span className={`badge ${d.status}`}>{STATUS_LABEL[d.status]}</span>
                  <SourceRefs ids={d.sources} sources={sources} />
                </div>
                {d.reason && <p>{d.reason}</p>}
                {d.where_to_get && <p className="meta">Unde: {d.where_to_get}</p>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {steps.length > 0 && (
        <section>
          <h4>Pași de urmat</h4>
          <ol className="step-list">
            {steps.map((s, i) => (
              <li key={i}>
                <div className="doc-head">
                  <strong>{s.title}</strong>
                  <SourceRefs ids={s.sources} sources={sources} />
                </div>
                {s.description && <p>{s.description}</p>}
                <p className="meta">
                  {[
                    s.where && `Unde: ${s.where}`,
                    s.cost && `Cost: ${s.cost}`,
                    s.duration && `Durată: ${s.duration}`,
                    s.depends_on_step && `După pasul ${s.depends_on_step}`,
                  ]
                    .filter(Boolean)
                    .join("  ·  ")}
                </p>
                {s.link && (
                  <a className="step-link" href={s.link} target="_blank" rel="noreferrer">
                    Deschide pagina oficială
                  </a>
                )}
              </li>
            ))}
          </ol>
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
  const endRef = useRef(null);
  const voice = useSpeech(setMessage);

  const push = (...items) => setConversation((old) => [...old, ...items]);

  const ask = async (question, answers = {}) => {
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, category: "auto", country: "auto", answers }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Serverul a răspuns cu eroarea ${res.status}.`);
      }
      const data = await res.json();

      if (data.needs_clarification && data.questions?.length) {
        setPending({ question, answers });
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
      } else if (/10061|refused|ConnectError|timed out/i.test(text)) {
        text =
          "Ollama nu rulează sau nu răspunde. Pornește aplicația Ollama (sau rulează `ollama serve`) " +
          "și verifică dacă modelul este instalat: `ollama pull llama3.2:3b`. Detalii: " + text;
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

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation, busy]);

  const sendMessage = (text) => {
    if (busy || !text.trim()) return;
    voice.cancel();
    push({ role: "user", type: "text", text });
    setMessage("");
    setPending(null);
    ask(text);
  };

  const answerQuestion = (q, value, label) => {
    if (busy || !pending) return;
    push({ role: "user", type: "text", text: label });
    ask(pending.question, { ...pending.answers, [q.key]: value });
  };

  const newChat = () => {
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
              {category.title}
            </button>
          ))}
        </nav>

        <div className="recent-conversations">
          <strong>Conversații recente</strong>
          {["Erasmus în Franța", "Înregistrare la medic", "Permis de ședere", "Deschidere firmă"].map((item) => (
            <button key={item} onClick={() => sendMessage(item)}>
              {item}
            </button>
          ))}
        </div>
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <strong>Asistent DocuGuide</strong>
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

        {voice.error && <p className="voice-error">{voice.error}</p>}

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
            placeholder={voice.listening ? "Te ascult..." : "Scrie un mesaj..."}
            aria-label="Scrie un mesaj"
            disabled={busy}
          />
          <MicButton voice={voice} disabled={busy} />
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
