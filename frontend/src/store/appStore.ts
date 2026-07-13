import { create } from "zustand";

interface AppState {
  activeSessionId: string | null;
  activeKb: string | null;
  provider: string | null;
  model: string | null;
  topK: number;
  setActiveSession: (id: string | null) => void;
  setActiveKb: (kb: string | null) => void;
  setProvider: (p: string | null) => void;
  setModel: (m: string | null) => void;
  setTopK: (k: number) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeSessionId: null,
  activeKb: null,
  provider: null,
  model: null,
  topK: 4,
  setActiveSession: (id) => set({ activeSessionId: id }),
  setActiveKb: (kb) => set({ activeKb: kb }),
  setProvider: (p) => set({ provider: p, model: null }),
  setModel: (m) => set({ model: m }),
  setTopK: (k) => set({ topK: k }),
}));
