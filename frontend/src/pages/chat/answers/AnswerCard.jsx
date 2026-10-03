import { DocumentList } from "./DocumentList.jsx";
import { StepList } from "./StepList.jsx";

// "Neconfirmat în surse: …" items are collapsed; notes that change what you do stay visible
const UNCONFIRMED = /^Neconfirmat în surse:\s*/;

export function AnswerCard({ data }) {
  const { answer, sources = [], card } = data;
  const documents = answer.documents || [];
  const steps = answer.steps || [];
  const warnings = answer.warnings || [];
  const contradictions = answer.contradictions || [];
  const extracts = answer.extracts || [];

  const unconfirmed = warnings.filter((w) => UNCONFIRMED.test(w)).map((w) => w.replace(UNCONFIRMED, ""));
  const visibleWarnings = warnings.filter((w) => !UNCONFIRMED.test(w));
  const guideKey = card?.id || `ad-hoc:${(answer.summary || "").slice(0, 40)}`;

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

      {steps.length > 0 && <StepList steps={steps} sources={sources} />}

      {documents.length > 0 && <DocumentList documents={documents} sources={sources} guideKey={guideKey} />}

      {extracts.length > 0 && (
        <section>
          <h4>Fragmente din sursele oficiale</h4>
          {extracts.map((e, i) => (
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
