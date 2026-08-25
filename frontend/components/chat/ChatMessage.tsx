import type { FC } from "react";

export interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  isLoading?: boolean;
}

const ChatMessage: FC<ChatMessageProps> = ({ role, content, isLoading }) => {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-secondary text-secondary-foreground rounded-bl-sm border border-border"
        } ${isLoading ? "animate-pulse" : ""}`}
      >
        {content}
      </div>
    </div>
  );
};

export default ChatMessage;
