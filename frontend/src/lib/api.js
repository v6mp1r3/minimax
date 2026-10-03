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
