import { useState } from "react";
import { Icon } from "../../../components/Icon.jsx";
import { loadChecks, saveChecks } from "../../../lib/storage.js";
import { SourceRefs, SourceToggle } from "./SourceParts.jsx";

const STATUS_LABEL = {
  required: "Obligatoriu",
  possible: "Posibil",
  recommended: "Recomandat",
  unknown: "Neconfirmat",
};

// Document checklist, remembered in this browser (keyed by guide + document name)
export function DocumentList({ documents, sources, guideKey }) {
  const [checks, setChecks] = useState(loadChecks);
  const byId = Object.fromEntries(sources.map((s) => [s.id, s]));

  const isChecked = (name) => !!checks[`${guideKey}:${name}`];
  const toggleCheck = (name) => {
    const next = { ...checks, [`${guideKey}:${name}`]: !isChecked(name) };
    setChecks(next);
    saveChecks(next);
  };
  const done = documents.filter((d) => isChecked(d.name)).length;

  return (
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
              {d.check === "confirmed" && (
                <span className="tick" title="Confirmat acum pe pagina oficială">
                  <Icon name="check" size={14} strokeWidth={2.75} />
                </span>
              )}
              <SourceRefs ids={d.sources} sources={sources} />
            </label>
            {d.applies === "yes" && <p className="meta"><span className="chip applies">Se aplică în cazul tău</span></p>}
            {d.applies === "maybe" && d.condition_text && <p className="meta"><span className="chip maybe">Doar dacă {d.condition_text}</span></p>}
            {d.reason && d.check !== "confirmed" && <p>{d.reason}</p>}
            {d.where_to_get && <p className="meta">Unde: {d.where_to_get}</p>}
            <SourceToggle quotes={d.quote ? [d.quote] : []} url={byId[(d.sources || [])[0]]?.url} />
          </li>
        ))}
      </ul>
    </section>
  );
}
