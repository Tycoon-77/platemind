import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ChatState {
  sessionId: string;
  isOpen: boolean;
  prefillMessage: string;
  setSessionId: (id: string) => void;
  clearSession: () => void;
  openChatWithPrefill: (msg: string) => void;
  setIsOpen: (isOpen: boolean) => void;
  setPrefillMessage: (msg: string) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      sessionId: "new",
      isOpen: false,
      prefillMessage: "",
      setSessionId: (id) => set({ sessionId: id }),
      clearSession: () => set({ sessionId: "new" }),
      openChatWithPrefill: (msg) => set({ isOpen: true, prefillMessage: msg }),
      setIsOpen: (isOpen) => set({ isOpen }),
      setPrefillMessage: (msg) => set({ prefillMessage: msg }),
    }),
    {
      name: 'platemind-chat-storage', // saves to localStorage
    }
  )
);
