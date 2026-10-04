// The only place that talks to the FastAPI backend.

export async function requestGuide({ question, answers, context }) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, category: "auto", country: "auto", answers, context }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Serverul a răspuns cu eroarea ${res.status}.`);
  }
  return res.json();
}

// Asks the server to build the PDF of the guide on screen; returns { url, name }.
// The url is a normal download link ("attachment" response), so the browser saves a real .pdf file.
export async function exportGuidePdf({ question, data, checked }) {
  const res = await fetch("/api/export/pdf/prepare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, data, checked }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Nu am putut genera PDF-ul (eroarea ${res.status}).`);
  }
  return res.json();
}

// Starts a native browser download of that url (stays on the page, no new tab)
export function saveFile(url, name) {
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// Turns a failed request into a message the user can act on
export function friendlyError(e) {
  if (e instanceof TypeError) {
    return "Nu mă pot conecta la server. Pornește backend-ul (run.bat / run.sh) și încearcă din nou.";
  }
  if (/10061|refused|ConnectError|timed out|Ollama/i.test(e.message)) {
    return (
      "Serviciul AI nu răspunde. Verifică cheia GROQ_API_KEY din fișierul .env, sau pornește Ollama " +
      "(`ollama serve`, modelul: `ollama pull llama3.2:3b`). Detalii: " + e.message
    );
  }
  return e.message;
}
