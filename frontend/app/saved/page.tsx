/* eslint-disable */
"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { useAuthStore } from "@/stores/authStore";
import RecipeCard from "@/components/recipe/RecipeCard";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { BookmarkIcon, ChefHatIcon } from "lucide-react";
import { toast } from "sonner";

export default function SavedPage() {
  const { userId, token } = useAuthStore();
  const [favorites, setFavorites] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!userId || !token) {
      setIsLoading(false);
      return;
    }

    const fetchFavorites = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/favorites/${userId}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to load favorites");
        const data = await res.json();
        setFavorites(data.favorites || []);
      } catch (err) {
        toast.error("Could not load saved recipes");
      } finally {
        setIsLoading(false);
      }
    };

    fetchFavorites();
  }, [userId, token]);

  if (!userId) {
    return (
      <PageShell>
        <div className="max-w-xl mx-auto py-20 text-center space-y-6">
          <BookmarkIcon className="w-16 h-16 mx-auto text-primary opacity-50" />
          <h1 className="text-3xl font-serif font-bold text-foreground">Saved Recipes</h1>
          <p className="text-muted-foreground text-lg">Sign up or log in to view and manage your saved recipes.</p>
          <div className="pt-6">
            <Link href="/signup" className="bg-primary text-primary-foreground px-8 py-3 rounded-full font-bold shadow-sm hover:bg-primary/90 transition-all text-lg">
              Sign up
            </Link>
          </div>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="max-w-6xl mx-auto space-y-10 py-6 animate-in fade-in slide-in-from-bottom-4">
        
        <div className="space-y-1 border-b border-border pb-6">
          <h1 className="text-3xl font-serif font-bold text-foreground flex items-center gap-2">
            <BookmarkIcon className="w-7 h-7 text-primary" fill="currentColor" />
            Saved Recipes
          </h1>
          <p className="text-muted-foreground">Your personal collection of favorites.</p>
        </div>

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="space-y-3">
                <Skeleton className="h-48 w-full rounded-xl" />
                <Skeleton className="h-6 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ))}
          </div>
        ) : favorites.length === 0 ? (
          <div className="text-center py-24 bg-card border border-dashed border-border rounded-2xl">
            <ChefHatIcon className="w-16 h-16 mx-auto text-muted-foreground opacity-30 mb-4" />
            <h2 className="text-2xl font-serif font-bold text-foreground mb-2">Nothing saved yet</h2>
            <p className="text-muted-foreground mb-6">Go find something delicious to cook!</p>
            <Link href="/" className="bg-primary text-primary-foreground px-8 py-3 rounded-full font-bold shadow-sm hover:bg-primary/90 transition-all">
              Discover Recipes
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {favorites.map((recipe) => (
              <RecipeCard
                key={recipe.recipe_id}
                id={recipe.recipe_id}
                name={recipe.name}
                totalMinutes={recipe.minutes}
              />
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
