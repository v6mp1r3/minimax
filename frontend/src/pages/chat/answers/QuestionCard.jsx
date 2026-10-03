import { useState } from "react";
import { Icon } from "../../../components/Icon.jsx";

export function QuestionCard({ q, active, onSubmit }) {
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
            <span className="option-mark">
              <Icon name={isMulti ? (picked.includes(o.value) ? "check" : "plus") : "next"} size={18} />
            </span>
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
