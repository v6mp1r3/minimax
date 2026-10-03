import { useEffect, useRef } from "react";
import { Avatar } from "../../components/Avatar.jsx";
import { AnswerCard } from "./answers/AnswerCard.jsx";
import { FollowupCard } from "./answers/FollowupCard.jsx";
import { QuestionCard } from "./answers/QuestionCard.jsx";
import { ThinkingBubble } from "./ThinkingBubble.jsx";

const sideOf = (m) => (m.role === "user" ? "user" : "assistant");

function MessageBody({ item, active, onAnswer }) {
  switch (item.type) {
    case "question":
      return <QuestionCard q={item.q} active={active} onSubmit={(value, label) => onAnswer(item.q, value, label)} />;
    case "followup":
      return (
        <div className="assistant-bubble answer-bubble">
          <FollowupCard data={item.data.followup} />
        </div>
      );
    case "answer":
      return (
        <div className="assistant-bubble answer-bubble">
          <AnswerCard data={item.data} />
        </div>
      );
    default:
      return <div className={item.role === "user" ? "user-bubble" : "assistant-bubble"}>{item.text}</div>;
  }
}

export function MessageList({ conversation, busy, onAnswer }) {
  const endRef = useRef(null);
  const lastIndex = conversation.length - 1;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation, busy]);

  // Instagram-style grouping: consecutive messages from the same side form one cluster,
  // and only the last bubble of an assistant cluster shows the avatar.
  const nextSide = (index) =>
    index < lastIndex ? sideOf(conversation[index + 1]) : busy ? "assistant" : null;

  return (
    <div className="chat-messages">
      {conversation.length === 0 && (
        <div className="chat-welcome">
          <Avatar />
          <div className="assistant-bubble">
            Bună! Sunt asistentul DocuGuide. Spune-mi ce documente
            sau procedură te interesează.
          </div>
        </div>
      )}

      {conversation.map((item, index) => {
        const side = sideOf(item);
        const joinsPrev = index > 0 && sideOf(conversation[index - 1]) === side;
        const joinsNext = nextSide(index) === side;
        return (
          <div
            className={`message-row ${side === "user" ? "user-row" : ""} ${joinsPrev ? "joins-prev" : ""} ${joinsNext ? "joins-next" : ""}`}
            key={index}
          >
            {side === "assistant" && (joinsNext ? <span className="avatar-spacer" /> : <Avatar />)}
            <MessageBody item={item} active={index === lastIndex && !busy} onAnswer={onAnswer} />
          </div>
        );
      })}

      {busy && (
        <div className={`message-row ${lastIndex >= 0 && sideOf(conversation[lastIndex]) === "assistant" ? "joins-prev" : ""}`}>
          <Avatar thinking />
          <ThinkingBubble />
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
