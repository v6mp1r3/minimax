import { Icon } from "../../../components/Icon.jsx";
import { SourceRefs, SourceToggle } from "./SourceParts.jsx";

export function StepList({ steps, sources }) {
  return (
    <section>
      <h4>Pași de urmat</h4>
      <ol className="step-list">
        {steps.map((s, i) => (
          <li key={i}>
            <div className="doc-head">
              <strong>{s.title}</strong>
              {s.check === "confirmed" && (
                <span className="tick" title="Confirmat acum pe pagina oficială">
                  <Icon name="check" size={14} strokeWidth={2.75} />
                </span>
              )}
              {s.check && s.check !== "confirmed" && (
                <span className="badge unknown">
                  {s.check === "changed" ? "Pagină schimbată" : "Neverificat acum"}
                </span>
              )}
              <SourceRefs ids={s.sources} sources={sources} />
            </div>
            {s.description && <p>{s.description}</p>}
            {(s.where || s.cost || s.duration || s.depends_on_step || s.applies) && (
              <div className="chips">
                {s.applies === "yes" && <span className="chip applies">Se aplică în cazul tău</span>}
                {s.applies === "maybe" && s.condition_text && <span className="chip maybe">Doar dacă {s.condition_text}</span>}
                {s.where && <span className="chip"><Icon name="location" size={13} /> {s.where}</span>}
                {s.cost && <span className="chip"><Icon name="cost" size={13} /> {s.cost}</span>}
                {s.duration && <span className="chip"><Icon name="time" size={13} /> {s.duration}</span>}
                {s.depends_on_step && <span className="chip">după pasul {s.depends_on_step}</span>}
              </div>
            )}
            <SourceToggle quotes={s.quotes || (s.quote ? [s.quote] : [])} url={s.link} />
          </li>
        ))}
      </ol>
    </section>
  );
}
