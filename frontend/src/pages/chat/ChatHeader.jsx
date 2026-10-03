import { Avatar } from "../../components/Avatar.jsx";
import { Icon } from "../../components/Icon.jsx";

export function ChatHeader({ busy, category, onHome }) {
  return (
    <header className={`chat-header ${busy ? "busy" : ""}`}>
      <div className="chat-header-id">
        <Avatar thinking={busy} />
        <div className="chat-header-text">
          <strong>Asistent DocuGuide</strong>
          <small className={busy ? "typing" : ""}>{busy ? "Scrie…" : "Activ acum"}</small>
        </div>
      </div>
      {category && (
        <span className="chat-category">
          <Icon name={category.icon} size={14} />
          {category.title}
        </span>
      )}
      <button className="mobile-home" onClick={onHome}>Acasă</button>
    </header>
  );
}
