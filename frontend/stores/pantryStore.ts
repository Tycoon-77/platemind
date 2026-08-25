/**
 * pantryStore.ts — Zustand store for client-side pantry state.
 *
 * Manages the in-session ingredient list used for recommendation.
 * For authenticated users, this syncs with the backend /pantry API (Phase 5).
 * For anonymous users ("try without account"), this is local-only.
 */
import { create } from "zustand";

export interface PantryIngredient {
  id?: number;          // ingredient_id from the DB (populated after Phase 4)
  name: string;
}

interface PantryState {
  ingredients: PantryIngredient[];
  addIngredient: (ingredient: PantryIngredient) => void;
  removeIngredient: (name: string) => void;
  clearPantry: () => void;
}

export const usePantryStore = create<PantryState>((set) => ({
  ingredients: [],

  addIngredient: (ingredient) =>
    set((state) => {
      // Prevent duplicates (case-insensitive)
      const exists = state.ingredients.some(
        (i) => i.name.toLowerCase() === ingredient.name.toLowerCase()
      );
      if (exists) return state;
      return { ingredients: [...state.ingredients, ingredient] };
    }),

  removeIngredient: (name) =>
    set((state) => ({
      ingredients: state.ingredients.filter(
        (i) => i.name.toLowerCase() !== name.toLowerCase()
      ),
    })),

  clearPantry: () => set({ ingredients: [] }),
}));
