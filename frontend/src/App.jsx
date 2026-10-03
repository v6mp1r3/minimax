import { useState } from "react";
import "./App.css";

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

function ChatPage({ initialMessage, onHome }) {
  const [message, setMessage] = useState("");
  const [selectedOption, setSelectedOption] = useState("");
  const [conversation, setConversation] = useState(
    initialMessage
      ? [{ role: "user", text: initialMessage }]
      : []
  );

  const [showQuestion, setShowQuestion] = useState(true);

  const sendMessage = (text) => {
    if (!text.trim()) return;

    setConversation((old) => [
      ...old,
      { role: "user", text },
      {
        role: "assistant",
        text: "Pentru a-ți pregăti un ghid personalizat, am nevoie de câteva detalii:",
      },
    ]);
    setMessage("");
    setShowQuestion(true);
    setSelectedOption("");
  };

  const chooseOption = (option) => {
    setSelectedOption(option);
    setConversation((old) => [
      ...old,
      { role: "user", text: option },
      {
        role: "assistant",
        text: "Mulțumesc! Aceasta este o demonstrație a interfeței. În versiunea finală, DocuGuide va continua cu întrebări adaptate răspunsului tău.",
      },
    ]);
    setShowQuestion(false);
  };

  return (
    <main className="chat-layout">
      <aside className="chat-sidebar">
        <Logo onClick={onHome} />

        <button
          className="new-chat-button"
          onClick={() => {
            setConversation([]);
            setShowQuestion(true);
            setSelectedOption("");
          }}
        >
          + Conversație nouă
        </button>

        <button className="all-conversations">
          Toate conversațiile
        </button>

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
              {item.role === "assistant" && (
                <span className="chat-avatar">♧</span>
              )}
              <div className={item.role === "user" ? "user-bubble" : "assistant-bubble"}>
                {item.text}
              </div>
            </div>
          ))}

          {showQuestion && conversation.length > 0 && (
            <div className="message-row">
              <span className="chat-avatar">♧</span>
              <div className="assistant-bubble question-bubble">
                <strong>La ce etapă te afli?</strong>
                <p>Alege varianta care descrie cel mai bine situația ta.</p>

                <div className="answer-options">
                  {["Vreau să aplic", "Am fost selectat", "Am început pregătirile"].map((option) => (
                    <button
                      key={option}
                      className={selectedOption === option ? "selected" : ""}
                      onClick={() => chooseOption(option)}
                    >
                      {option}
                      <span>›</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
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
          />
          <button type="submit" className="chat-send" aria-label="Trimite">
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