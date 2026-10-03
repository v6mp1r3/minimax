import { useState } from "react";
import { Icon } from "../components/Icon.jsx";
import { categories, examples } from "../data/categories.js";

export function HomePage({ onChat, onCategory }) {
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
          <span><Icon name="spark" size={20} /></span>
          <div />
          <div />
        </div>

        <div className="hero-decoration decoration-two">
          <span><Icon name="spark" size={20} /></span>
          <div />
          <div />
        </div>

        <div className="hero-content">
          <div className="hero-label">
            <Icon name="spark" size={16} /> Asistent AI pentru documente
          </div>

          <h1>
            Orice situație. <span>Un singur ghid.</span>
          </h1>

          <p className="hero-description">
            Obține rapid informații despre documentele necesare,
            pașii de urmat și procedurile oficiale, pentru orice situație.
          </p>

          <div className="search-box">
            <span className="search-icon"><Icon name="search" size={22} /></span>
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
              <Icon name="go" size={20} />
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
                <Icon name={category.icon} size={24} />
              </span>

              <span className="category-text">
                <strong>{category.title}</strong>
                <small>{category.description}</small>
              </span>

              <span className="category-arrow"><Icon name="go" size={18} /></span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}
