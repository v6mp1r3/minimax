import { Icon } from "./Icon.jsx";

export function Logo({ onClick }) {
  return (
    <button className="logo" onClick={onClick} aria-label="DocuGuide - Acasă">
      <span className="logo-icon"><Icon name="logo" size={20} /></span>
      <span>DocuGuide</span>
    </button>
  );
}
