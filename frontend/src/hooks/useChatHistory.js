import { useEffect, useMemo, useState } from "react";
import { MAX_HISTORY, loadHistory, orderHistory, saveHistory } from "../lib/storage.js";

/**
 * History = the open conversation (kept up to date) + the ones saved earlier in this browser.
 */
export function useChatHistory(conversation, categoryId) {
  const [chatId, setChatId] = useState(() => String(Date.now()));
  const [rev, setRev] = useState(0); // bumped after pin / delete so the list is re-read

  const history = useMemo(() => {
    const firstUser = conversation.find((m) => m.role === "user");
    const all = loadHistory();
    const saved = all.filter((h) => h.id !== chatId);
    if (!firstUser) return orderHistory(saved);
    const pinned = !!all.find((h) => h.id === chatId)?.pinned;
    return orderHistory([
      { id: chatId, title: firstUser.text.slice(0, 48), categoryId, conversation, pinned },
      ...saved,
    ]).slice(0, MAX_HISTORY + 10);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversation, categoryId, chatId, rev]);

  useEffect(() => {
    if (conversation.length) saveHistory(history);
  }, [history, conversation.length]);

  const togglePin = (id) => {
    saveHistory(history.map((h) => (h.id === id ? { ...h, pinned: !h.pinned } : h)));
    setRev((r) => r + 1);
  };

  const remove = (id) => {
    saveHistory(history.filter((h) => h.id !== id));
    setRev((r) => r + 1);
  };

  const startNew = () => setChatId(String(Date.now()));

  return { history, chatId, setChatId, togglePin, remove, startNew };
}
