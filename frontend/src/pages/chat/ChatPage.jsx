import { useState } from "react";
import { ConfirmDialog } from "../../components/ConfirmDialog.jsx";
import { categoryById } from "../../data/categories.js";
import { useChat } from "../../hooks/useChat.js";
import { useChatHistory } from "../../hooks/useChatHistory.js";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition.js";
import { ChatHeader } from "./ChatHeader.jsx";
import { ChatSidebar } from "./ChatSidebar.jsx";
import { Composer } from "./Composer.jsx";
import { MessageList } from "./MessageList.jsx";

const SPEECH_LANG = "ro-RO"; // language used for dictation

export function ChatPage({ initialMessage, onHome }) {
  const [message, setMessage] = useState("");
  const [deleteTarget, setDeleteTarget] = useState(null); // history item waiting for confirmation

  const chat = useChat(initialMessage);
  const log = useChatHistory(chat.conversation, chat.categoryId);
  const speech = useSpeechRecognition({ lang: SPEECH_LANG, onTranscript: setMessage });

  const sendMessage = (text) => {
    if (chat.busy || !text.trim()) return;
    speech.abort(); // stop dictating; a late result must not refill the input
    setMessage("");
    chat.send(text);
  };

  const newChat = () => {
    if (chat.busy) return; // an answer is still on its way: it would land in the wrong conversation
    speech.abort();
    chat.reset();
    log.startNew();
    setMessage("");
  };

  const openHistory = (item) => {
    if (chat.busy) return;
    speech.abort();
    // an unanswered clarification question cannot be resumed: drop it
    const conv = [...item.conversation];
    while (conv.length && conv[conv.length - 1].type === "question") conv.pop();
    log.setChatId(item.id);
    chat.load(conv, item.categoryId);
    setMessage("");
  };

  const confirmDelete = () => {
    const id = deleteTarget?.id;
    setDeleteTarget(null);
    if (!id) return;
    log.remove(id);
    if (id === log.chatId) newChat(); // the open conversation is gone: start a clean one so it is not saved again
  };

  return (
    <main className="chat-layout">
      <ChatSidebar
        history={log.history}
        chatId={log.chatId}
        busy={chat.busy}
        onHome={onHome}
        onNewChat={newChat}
        onAsk={sendMessage}
        onOpen={openHistory}
        onTogglePin={log.togglePin}
        onDelete={setDeleteTarget}
      />

      <section className="chat-main">
        <ChatHeader busy={chat.busy} category={categoryById(chat.categoryId)} onHome={onHome} />
        <MessageList conversation={chat.conversation} busy={chat.busy} onAnswer={chat.answer} />
        <Composer
          message={message}
          onChange={setMessage}
          onSubmit={sendMessage}
          busy={chat.busy}
          speech={speech}
        />
      </section>

      {deleteTarget && (
        <ConfirmDialog
          title="Ștergi conversația?"
          text={`„${deleteTarget.title}” va fi ștearsă definitiv din istoric. Nu poți anula această acțiune.`}
          confirmLabel="Șterge"
          onConfirm={confirmDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </main>
  );
}
