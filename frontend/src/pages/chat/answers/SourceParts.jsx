export function SourceRefs({ ids = [], sources }) {
  if (sources.length <= 1) return null; // with one source the number says nothing and looks like a step number
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

// Verbatim official quote(s) + link, hidden until asked for
export function SourceToggle({ quotes = [], url }) {
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
