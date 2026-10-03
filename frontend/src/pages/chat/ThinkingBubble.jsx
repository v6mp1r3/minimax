// "DocuGuide is typing": just three bouncing dots in a bubble, while the backend works.
export function ThinkingBubble() {
  return (
    <div className="assistant-bubble thinking" role="status" aria-label="DocuGuide scrie un răspuns">
      <span className="thinking-dots" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
    </div>
  );
}
