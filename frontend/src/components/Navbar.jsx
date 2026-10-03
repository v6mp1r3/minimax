import { Logo } from "./Logo.jsx";

export function Navbar({ onHome, onChat }) {
  return (
    <header className="navbar">
      <Logo onClick={onHome} />

      <div className="navbar-actions">
        <button className="language-button">RO</button>
        <button className="primary-button" onClick={onChat}>
          Deschide Chat
        </button>
      </div>
    </header>
  );
}
