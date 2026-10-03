import { useCallback, useEffect, useRef, useState } from "react";

// Browser speech-to-text (Web Speech API). Chrome, Edge and Safari support it; Firefox does not.
const SR = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

const ERRORS = {
  "not-allowed": "Accesul la microfon este blocat. Permite-l din setările browserului și încearcă din nou.",
  "service-not-allowed": "Accesul la microfon este blocat. Permite-l din setările browserului și încearcă din nou.",
  "no-speech": "Nu am auzit nimic. Încearcă din nou.",
  "audio-capture": "Nu am găsit niciun microfon.",
  network: "Dictarea vocală are nevoie de conexiune la internet.",
  default: "Dictarea vocală nu a funcționat. Încearcă din nou.",
};

/**
 * Dictation into a text field.
 * `onTranscript(text)` receives the full text (what was already typed + what was dictated so far).
 * Use `abort()` when the text is being replaced or sent, so a late result cannot bring it back.
 */
export function useSpeechRecognition({ lang = "ro-RO", onTranscript }) {
  const recRef = useRef(null);
  const baseRef = useRef("");
  const callbackRef = useRef(onTranscript);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    callbackRef.current = onTranscript;
  });

  useEffect(() => {
    if (!error) return undefined;
    const id = setTimeout(() => setError(""), 6000);
    return () => clearTimeout(id);
  }, [error]);

  const start = useCallback(
    (existingText = "") => {
      if (!SR || recRef.current) return;
      setError("");
      const rec = new SR();
      rec.lang = lang;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      // Android Chrome repeats words in continuous mode, so it takes one phrase at a time there
      rec.continuous = !/Android/i.test(navigator.userAgent);
      baseRef.current = existingText.trim();

      rec.onstart = () => setListening(true);
      rec.onresult = (e) => {
        let spoken = "";
        for (let i = 0; i < e.results.length; i++) spoken += e.results[i][0].transcript;
        spoken = spoken.trim();
        const base = baseRef.current;
        callbackRef.current?.(base ? `${base} ${spoken}` : spoken);
      };
      rec.onerror = (e) => {
        if (e.error !== "aborted") setError(ERRORS[e.error] || ERRORS.default);
      };
      rec.onend = () => {
        recRef.current = null;
        setListening(false);
      };

      recRef.current = rec;
      try {
        rec.start();
      } catch {
        recRef.current = null;
      }
    },
    [lang]
  );

  const stop = useCallback(() => recRef.current?.stop(), []); // keeps what was heard
  const abort = useCallback(() => recRef.current?.abort(), []); // drops anything still pending

  useEffect(() => () => recRef.current?.abort(), []);

  return { supported: !!SR, listening, error, start, stop, abort };
}
