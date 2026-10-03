export function FollowupCard({ data }) {
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
