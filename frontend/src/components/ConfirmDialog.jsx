import { useEffect, useRef } from "react";
import { Icon } from "./Icon.jsx";

// In-app confirmation dialog (replaces window.confirm)
export function ConfirmDialog({ title, text, confirmLabel, cancelLabel = "Anulează", onConfirm, onCancel }) {
  const cancelRef = useRef(null);

  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && onCancel();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" onMouseDown={onCancel}>
      <div
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-text"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <span className="modal-icon"><Icon name="trash" size={22} /></span>
        <h3 id="confirm-title">{title}</h3>
        <p id="confirm-text">{text}</p>
        <div className="modal-actions">
          <button ref={cancelRef} className="modal-cancel" onClick={onCancel}>{cancelLabel}</button>
          <button className="modal-confirm" onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
