/* eslint-disable */

"use client";

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircleIcon, XIcon, SendIcon } from "lucide-react";
import ChatMessage, { type ChatMessageProps } from "./ChatMessage";
import { useChatStore } from "@/stores/chatStore";
import { toast } from "sonner";

export interface ChatPanelProps {
  onRecipesUpdated?: (recipes: Record<string, unknown>[]) => void;
}

const ChatPanel = ({ onRecipesUpdated }: ChatPanelProps) => {
  const { sessionId, setSessionId, isOpen, setIsOpen, prefillMessage, setPrefillMessage } = useChatStore();
  const [messages, setMessages] = useState<ChatMessageProps[]>([
    {
      role: "assistant",
      content: "Hi! I can help refine your recipe recommendations. Try: \"make it vegetarian\", \"under 30 minutes\", or \"swap the cilantro\".",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (prefillMessage) {

      

      setInputValue(prefillMessage);
      setPrefillMessage("");
      if (inputRef.current) inputRef.current.focus();
    }
  }, [prefillMessage, setPrefillMessage]);

  const sendMessage = async () => {
    const text = inputValue.trim();
    if (!text || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInputValue("");
    setIsLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
        }),
      });

      const data = await res.json();
      
      if (!res.ok) {
        if (res.status === 429) {
          throw new Error("We're experiencing high traffic. Please wait a moment before trying again.");
        }
        throw new Error(data.detail || "Failed to process chat message");
      }

      if (sessionId === "new" && data.session_id) {
        setSessionId(data.session_id);
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply },
      ]);

      if (data.updated_results && data.updated_results.length > 0) {
        const withReason = data.updated_results.map((r: Record<string, unknown>) => ({
          ...r,
          match_reason: r.match_reason || "Recommended by Assistant"
        }));
        onRecipesUpdated?.(withReason);
      }
      
    } catch (err: unknown) {
      console.error(err);
      toast.error((err as Error).message || "Failed to send message. Please try again.");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "I'm sorry, I'm having trouble connecting to the brain. Please try again in a moment." }
      ]);
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 100);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <>
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 rounded-full bg-primary text-primary-foreground p-4 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all duration-200"
            aria-label="Open chat"
          >
            <MessageCircleIcon className="w-6 h-6" />
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {isOpen && (
          <motion.aside
            initial={{ y: "100%", opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: "100%", opacity: 0 }}
            transition={{ type: "spring", bounce: 0, duration: 0.4 }}
            className="fixed bottom-0 right-0 sm:right-6 sm:bottom-6 z-50 w-full sm:w-[400px] h-[75vh] sm:h-[600px] flex flex-col bg-card border border-border sm:rounded-2xl shadow-2xl overflow-hidden"
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-secondary/30">
              <div className="flex items-center gap-2">
                <MessageCircleIcon className="w-5 h-5 text-primary" />
                <h2 className="font-semibold text-foreground">Recipe Assistant</h2>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-secondary"
                aria-label="Close chat"
              >
                <XIcon className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-background flex flex-col">
              {messages.map((msg, i) => (
                <ChatMessage key={i} role={msg.role} content={msg.content} />
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-secondary text-secondary-foreground rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm border border-border max-w-[85%]">
                    <span className="flex space-x-1 items-center h-4">
                      <motion.span className="w-1.5 h-1.5 bg-muted-foreground rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0 }} />
                      <motion.span className="w-1.5 h-1.5 bg-muted-foreground rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.2 }} />
                      <motion.span className="w-1.5 h-1.5 bg-muted-foreground rounded-full" animate={{ y: [0, -4, 0] }} transition={{ duration: 0.6, repeat: Infinity, delay: 0.4 }} />
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4 bg-card border-t border-border">
              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question..."
                  className="flex-1 rounded-full border border-border bg-background px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
                />
                <button
                  onClick={sendMessage}
                  disabled={!inputValue.trim() || isLoading}
                  className="rounded-full bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground w-11 h-11 flex items-center justify-center transition-all shadow-sm flex-shrink-0"
                >
                  <SendIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
};

export default ChatPanel;
