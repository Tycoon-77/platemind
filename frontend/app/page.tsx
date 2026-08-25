"use client";

import { PageShell } from "@/components/layout/PageShell";
import PantryInput from "@/components/pantry/PantryInput";
import RecipeCard from "@/components/recipe/RecipeCard";
import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

interface RecipeResult {
  recipe_id: number;
  name: string;
  minutes: number;
  tags: string[];
  ingredients: string[];
  match_reason: string;
}

import { useDashboardStore } from "@/stores/dashboardStore";

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const { recipes, setRecipes, pantryItems, setPantryItems } = useDashboardStore();
  const hasSearched = recipes.length > 0;

  const handleSearch = async (ingredients: string[]) => {
    setIsLoading(true);
    setPantryItems(ingredients);
    setRecipes([]);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recommend/pantry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ingredients: ingredients
        })
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      setRecipes(data.results || []);
      
      if (data.results?.length > 0) {
        toast.success("Recipes loaded successfully!");
      } else {
        toast.info("No recipes matched your exact ingredients. Try adding more staples!");
      }
    } catch (err: unknown) {
      console.error(err);
      toast.error("Failed to fetch recipes. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageShell onRecipesUpdated={(updatedRecipes) => {
      setRecipes(updatedRecipes as unknown as RecipeResult[]);
    }}>
      <div className="max-w-6xl mx-auto space-y-10">
        
        {/* Header section */}
        <div className="text-center space-y-4">
          <h1 className="text-4xl md:text-5xl font-serif font-bold tracking-tight text-primary">
            What&apos;s for dinner?
          </h1>
          <p className="text-muted-foreground text-lg max-w-xl mx-auto">
            Tell us what you have in your pantry, and we&apos;ll generate the perfect recipe using our intelligent recommendation engine.
          </p>
        </div>

        {/* Pantry Input Component */}
        <div className="bg-card p-6 md:p-8 rounded-2xl shadow-sm border border-border">
          <PantryInput onSearch={handleSearch} initialTags={pantryItems} />
        </div>

        {/* Results section */}
        {hasSearched && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-serif font-semibold text-foreground">Recommended for you</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {isLoading ? (
                <>
                  <div className="flex flex-col space-y-3">
                    <Skeleton className="h-48 w-full rounded-xl" />
                    <div className="space-y-2">
                      <Skeleton className="h-6 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                    </div>
                  </div>
                  <div className="flex flex-col space-y-3">
                    <Skeleton className="h-48 w-full rounded-xl" />
                    <div className="space-y-2">
                      <Skeleton className="h-6 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                    </div>
                  </div>
                </>
              ) : (
                recipes.map((recipe) => (
                  <RecipeCard
                    key={recipe.recipe_id}
                    id={recipe.recipe_id}
                    name={recipe.name}
                    totalMinutes={recipe.minutes}
                    matchReason={recipe.match_reason}
                  />
                ))
              )}
            </div>
          </div>
        )}

      </div>
    </PageShell>
  );
}
