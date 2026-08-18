import { create } from "zustand";

export interface ToolEventVM {
  name: string;
  ok: boolean;
}

export interface ChatMessageVM {
  role: "user" | "assistant" | "tool";
  content: string;
  toolEvents?: ToolEventVM[];
}

export interface SessionVM {
  id: string;
  createdAt: string;
}

interface ChatState {
  sessions: SessionVM[];
  activeSessionId: string | null;
  messagesBySession: Record<string, ChatMessageVM[]>;
  setSessions: (sessions: SessionVM[]) => void;
  setActiveSession: (id: string) => void;
  setMessages: (sessionId: string, messages: ChatMessageVM[]) => void;
  appendMessage: (sessionId: string, message: ChatMessageVM) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  sessions: [],
  activeSessionId: null,
  messagesBySession: {},
  setSessions: (sessions) => set({ sessions }),
  setActiveSession: (id) => set({ activeSessionId: id }),
  setMessages: (sessionId, messages) =>
    set((state) => ({
      messagesBySession: { ...state.messagesBySession, [sessionId]: messages },
    })),
  appendMessage: (sessionId, message) =>
    set((state) => ({
      messagesBySession: {
        ...state.messagesBySession,
        [sessionId]: [...(state.messagesBySession[sessionId] ?? []), message],
      },
    })),
}));
