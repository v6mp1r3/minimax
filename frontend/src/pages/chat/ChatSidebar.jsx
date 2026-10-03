import { Icon } from "../../components/Icon.jsx";
import { Logo } from "../../components/Logo.jsx";
import { categories, categoryById } from "../../data/categories.js";

function HistoryItem({ item, active, busy, onOpen, onTogglePin, onDelete }) {
  const c = categoryById(item.categoryId);
  return (
    <div className={`recent-item ${active ? "active" : ""} ${item.pinned ? "pinned" : ""}`}>
      <button
        className="recent-open"
        onClick={() => onOpen(item)}
        disabled={busy && !active}
        title={c ? c.title : "Conversație"}
      >
        <span className="side-icon"><Icon name={c ? c.icon : "chat"} size={16} /></span>
        <span className="recent-title">{item.title}</span>
        {item.pinned && (
          <span className="pin-mark" aria-label="Fixată">
            <Icon name="pin" size={12} fill="currentColor" />
          </span>
        )}
      </button>
      <div className="recent-actions">
        <button
          className="icon-action"
          onClick={() => onTogglePin(item.id)}
          title={item.pinned ? "Anulează fixarea" : "Fixează în partea de sus"}
          aria-label={item.pinned ? "Anulează fixarea" : "Fixează conversația"}
        >
          <Icon name={item.pinned ? "unpin" : "pin"} size={15} />
        </button>
        <button
          className="icon-action danger"
          onClick={() => onDelete(item)}
          disabled={busy && active}
          title={busy && active ? "Așteaptă finalizarea răspunsului" : "Șterge conversația"}
          aria-label="Șterge conversația"
        >
          <Icon name="trash" size={15} />
        </button>
      </div>
    </div>
  );
}

export function ChatSidebar({ history, chatId, busy, onHome, onNewChat, onAsk, onOpen, onTogglePin, onDelete }) {
  return (
    <aside className="chat-sidebar">
      <div className="sidebar-brand">
        <Logo onClick={onHome} />
      </div>

      <button
        className="new-chat-button"
        onClick={onNewChat}
        disabled={busy}
        title={busy ? "Așteaptă finalizarea răspunsului" : undefined}
      >
        <Icon name="plus" size={16} /> Conversație nouă
      </button>

      <button className="all-conversations">Toate conversațiile</button>

      <nav className="sidebar-categories">
        {categories.map((category) => (
          <button
            key={category.id}
            disabled={busy}
            onClick={() => onAsk(`Vreau informații despre ${category.title}`)}
          >
            <span className="side-icon"><Icon name={category.icon} size={16} /></span>
            {category.title}
          </button>
        ))}
      </nav>

      <div className="recent-conversations">
        <strong>Conversații recente</strong>
        {history.length === 0 && <small className="recent-empty">Încă nu ai conversații.</small>}
        {history.map((item) => (
          <HistoryItem
            key={item.id}
            item={item}
            active={item.id === chatId}
            busy={busy}
            onOpen={onOpen}
            onTogglePin={onTogglePin}
            onDelete={onDelete}
          />
        ))}
      </div>
    </aside>
  );
}
