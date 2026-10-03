import { Icon } from "../../components/Icon.jsx";

// Message box: text input, dictation (speech-to-text) and send button.
export function Composer({ message, onChange, onSubmit, busy, speech }) {
  return (
    <>
      {(speech.listening || speech.error) && (
        <div className={`speech-status ${speech.error ? "error" : ""}`} role="status" aria-live="polite">
          {speech.error ? (
            speech.error
          ) : (
            <>
              <span className="rec-dot" aria-hidden="true" /> Ascult… vorbește acum
            </>
          )}
        </div>
      )}

      <form
        className="chat-input-area"
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit(message);
        }}
      >
        <button type="button" className="add-button" aria-label="Adaugă">
          <Icon name="plus" size={20} />
        </button>
        <input
          value={message}
          onChange={(e) => {
            if (speech.listening) speech.abort(); // typing takes over from dictation
            onChange(e.target.value);
          }}
          placeholder={
            speech.listening
              ? "Vorbește acum…"
              : busy
                ? "DocuGuide lucrează… poți scrie următorul mesaj"
                : "Scrie un mesaj..."
          }
          aria-label="Scrie un mesaj"
        />
        {speech.supported && (
          <button
            type="button"
            className={`mic-button ${speech.listening ? "listening" : ""}`}
            onClick={() => (speech.listening ? speech.stop() : speech.start(message))}
            aria-pressed={speech.listening}
            aria-label={speech.listening ? "Oprește dictarea" : "Dictează mesajul"}
            title={speech.listening ? "Oprește dictarea" : "Dictează mesajul"}
          >
            <Icon
              name={speech.listening ? "stop" : "mic"}
              size={speech.listening ? 16 : 20}
              fill={speech.listening ? "currentColor" : "none"}
            />
          </button>
        )}
        <button type="submit" className="chat-send" aria-label="Trimite" disabled={busy || !message.trim()}>
          {busy ? <Icon name="loader" size={20} className="icon-spin" /> : <Icon name="send" size={20} />}
        </button>
      </form>
    </>
  );
}
