import { Icon } from "./Icon.jsx";

// Round avatar with a gradient ring (story-style). `thinking` pulses the ring while the AI works.
export function Avatar({ size = "md", thinking = false }) {
  return (
    <span className={`chat-avatar ${size} ${thinking ? "thinking-avatar" : ""}`} aria-hidden="true">
      <span className="avatar-inner">
        <Icon name="logo" size={size === "sm" ? 14 : 18} />
      </span>
    </span>
  );
}
