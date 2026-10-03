import { useState } from "react";
import { Icon } from "../components/Icon.jsx";

export function CategoryPage({ category, onChat, onHome }) {
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
          <Icon name={category.icon} size={30} />
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
                Vezi pașii <Icon name="go" size={16} />
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
          Întreabă DocuGuide <Icon name="go" size={16} />
        </button>
      </section>

      <button className="back-link" onClick={onHome}>
        <Icon name="back" size={16} /> Înapoi la pagina principală
      </button>
    </main>
  );
}
