import { useEffect, useRef, useState } from "react";
import { backendCategory } from "../data/categories.js";
import { friendlyError, requestGuide } from "../lib/api.js";

/**
 * Conversation state + the request flow with the backend:
 * a question may come back as an answer, a follow-up, or clarification questions (one at a time).
 */
export function useChat(initialMessage) {
  const [conversation, setConversation] = useState(
    initialMessage ? [{ role: "user", type: "text", text: initialMessage }] : []
  );
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null); // { question, answers, prev } while clarifying
  const [categoryId, setCategoryId] = useState(null);
  const started = useRef(false);
  const lastQuestion = useRef(""); // previous question, so a short follow-up can refer back to it

  const push = (...items) => setConversation((old) => [...old, ...items]);

  const currentCardId = () =>
    [...conversation].reverse().map((m) => m.data?.card?.id).find(Boolean) || null;

  const ask = async (question, answers = {}, prev = lastQuestion.current) => {
    const isNewQuestion = Object.keys(answers).length === 0;
    if (isNewQuestion) lastQuestion.current = question;
    setBusy(true);
    try {
      const data = await requestGuide({
        question,
        answers,
        // the guide on screen, so "de unde iau documentul X?" is answered from it
        context: { card_id: isNewQuestion ? currentCardId() : null, prev_question: prev },
      });

      const detected = backendCategory[data.category];
      if (detected) setCategoryId(detected);

      if (data.followup) {
        setPending(null);
        push({ role: "assistant", type: "followup", data });
      } else if (data.needs_clarification && data.questions?.length) {
        setPending({ question, answers, prev });
        const items = [];
        if (isNewQuestion) {
          items.push({
            role: "assistant",
            type: "text",
            text: "Pentru a-ți pregăti un ghid personalizat, am nevoie de câteva detalii:",
          });
        }
        items.push({ role: "assistant", type: "question", q: data.questions[0] });
        push(...items);
      } else {
        setPending(null);
        // keep the question with the answer: the PDF export prints it
        push({ role: "assistant", type: "answer", data: { ...data, question } });
      }
    } catch (e) {
      setPending(null);
      push({ role: "assistant", type: "text", text: friendlyError(e) });
    } finally {
      setBusy(false);
    }
  };

  // a chat opened from the home page starts by sending its first message
  useEffect(() => {
    if (initialMessage && !started.current) {
      started.current = true;
      ask(initialMessage);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const send = (text) => {
    if (busy || !text.trim()) return;
    push({ role: "user", type: "text", text });
    setPending(null);
    ask(text);
  };

  const answer = (q, value, label) => {
    if (busy || !pending) return;
    push({ role: "user", type: "text", text: label });
    ask(pending.question, { ...pending.answers, [q.key]: value }, pending.prev);
  };

  const reset = () => {
    lastQuestion.current = "";
    setCategoryId(null);
    setConversation([]);
    setPending(null);
  };

  const load = (savedConversation, savedCategoryId) => {
    setCategoryId(savedCategoryId);
    setConversation(savedConversation);
    setPending(null);
  };

  return { conversation, busy, categoryId, send, answer, reset, load };
}
