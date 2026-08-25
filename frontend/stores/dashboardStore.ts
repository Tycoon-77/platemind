import { create } from 'zustand';

interface RecipeResult {
  recipe_id: number;
  name: string;
  minutes: number;
  tags: string[];
  ingredients: string[];
  match_reason: string;
}

interface DashboardState {
  recipes: RecipeResult[];
  setRecipes: (recipes: RecipeResult[]) => void;
  pantryItems: string[];
  setPantryItems: (items: string[]) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  recipes: [],
  setRecipes: (recipes) => set({ recipes }),
  pantryItems: [],
  setPantryItems: (pantryItems) => set({ pantryItems }),
}));
