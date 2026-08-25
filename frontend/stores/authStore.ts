import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  userId: number | null;
  email: string | null;
  displayName: string | null;
  login: (token: string, userId: number, email: string, displayName?: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      email: null,
      displayName: null,
      login: (token, userId, email, displayName) => set({ token, userId, email, displayName: displayName || null }),
      logout: () => set({ token: null, userId: null, email: null, displayName: null }),
    }),
    {
      name: 'platemind-auth-storage', // saves to localStorage
    }
  )
);
