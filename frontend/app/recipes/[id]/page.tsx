"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { Skeleton } from "@/components/ui/skeleton";
import { ClockIcon, ChefHatIcon, BookmarkIcon, CheckCircleIcon, MessageCircleIcon } from "lucide-react";
import { toast } from "sonner";
import { useChatStore } from "@/stores/chatStore";
import { useAuthStore } from "@/stores/authStore";

interface RecipeDetail {
  recipe_id: number;
  name: string;
  minutes: number;
  description: string;
  ingredients: string[];
  tags: string[];
  steps: string[];
}

export default function RecipeDetailPage() {
  const params = useParams();
  const { id } = params;
  const router = useRouter();
  
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Real DB state (can refine this to fetch actual fav status later, 
  // for now we optimistically toggle after a successful POST)
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const { openChatWithPrefill } = useChatStore();
  const { token, userId } = useAuthStore();

  useEffect(() => {
    if (!id) return;
    
    const fetchRecipe = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recipes/${id}`);
        if (!res.ok) {
          if (res.status === 404) throw new Error("Recipe not found.");
          throw new Error("Failed to fetch recipe.");
        }
        const data = await res.json();
        setRecipe(data);
      } catch (err: unknown) {
        setError((err as Error).message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecipe();
  }, [id]);

  const handleSave = async () => {
    if (!token || !userId) {
      toast.info("Sign up to sync your favorites across devices!");
      router.push("/signup");
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/favorites/${userId}`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ recipe_id: Number(id) })
      });
      
      
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to save recipe");
      
      setIsSaved(true);
      toast.success("Recipe saved successfully!");
    } catch (err: unknown) {
      toast.error((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCooked = async () => {
    if (!token || !userId) {
      toast.info("Sign up or log in to track your cooking history!");
      router.push("/signup");
      return;
    }

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/favorites/${userId}/cooked`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ recipe_id: Number(id) })
      });
      
      
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to mark as cooked");
      
      toast.success("Marked as cooked! Great job.");
    } catch (err: unknown) {
      toast.error((err as Error).message);
    }
  };

  const handleAsk = () => {
    openChatWithPrefill(`Can I substitute an ingredient in ${recipe?.name}?`);
  };

  return (
    <PageShell>
      <div className="max-w-6xl mx-auto py-6">
        {isLoading && (
          <div className="space-y-6">
            <Skeleton className="h-12 w-3/4" />
            <div className="flex gap-4">
              <Skeleton className="h-6 w-24" />
              <Skeleton className="h-6 w-24" />
            </div>
            <Skeleton className="h-64 w-full rounded-2xl" />
          </div>
        )}

        {error && (
          <div className="text-center space-y-4 py-20">
            <div className="text-4xl">🍽️</div>
            <h2 className="text-2xl font-serif font-bold text-foreground">{error}</h2>
            <p className="text-muted-foreground">We couldn&apos;t find the recipe you&apos;re looking for.</p>
          </div>
        )}

        {recipe && !isLoading && !error && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-10">
            
            <div className="w-full h-64 md:h-80 rounded-2xl overflow-hidden mb-6 shadow-sm">
              <img src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recipes/${id}/image`} onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=1200&q=80"; }} alt={recipe.name} className="w-full h-full object-cover" />
            </div>
            
            <div className="space-y-6">

              <h1 className="text-4xl md:text-5xl font-serif font-bold text-foreground capitalize tracking-tight">
                {recipe.name}
              </h1>
              
              <div className="flex flex-wrap items-center gap-4 text-muted-foreground">
                <div className="flex items-center gap-1.5 font-medium">
                  <ClockIcon className="w-5 h-5" />
                  <span>{recipe.minutes} minutes</span>
                </div>
                <div className="flex items-center gap-1.5 font-medium first-letter:uppercase">
                  <ChefHatIcon className="w-5 h-5" />
                  <span>{recipe.tags.find(t => t.includes('cuisine') || t.includes('american') || t.includes('italian') || t.includes('mexican')) || "Mixed"}</span>
                </div>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {recipe.tags.slice(0, 5).map(tag => (
                  <span key={tag} className="px-3 py-1 bg-secondary text-secondary-foreground text-sm rounded-full first-letter:uppercase">
                    {tag.replace(/-/g, ' ')}
                  </span>
                ))}
              </div>

              {recipe.description && (
                <p className="text-lg text-foreground/80 leading-relaxed max-w-3xl">
                  {recipe.description}
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 py-6 border-y border-border">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className={`flex items-center gap-2 px-6 py-2.5 rounded-full font-semibold transition-all shadow-sm border disabled:opacity-70 ${
                  isSaved 
                    ? "bg-primary border-primary text-primary-foreground"
                    : "bg-background border-border hover:bg-secondary text-foreground"
                }`}
              >
                <BookmarkIcon className="w-5 h-5" fill={isSaved ? "currentColor" : "none"} />
                {isSaved ? "Saved" : "Save"}
              </button>
              
              <button
                onClick={handleCooked}
                className="flex items-center gap-2 px-6 py-2.5 rounded-full font-semibold bg-background border border-border hover:bg-secondary text-foreground transition-all shadow-sm"
              >
                <CheckCircleIcon className="w-5 h-5 text-muted-foreground" />
                I Cooked This
              </button>

              <button
                onClick={handleAsk}
                className="flex items-center gap-2 px-6 py-2.5 rounded-full font-semibold bg-secondary/50 border border-primary/20 text-primary hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all shadow-sm ml-auto"
              >
                <MessageCircleIcon className="w-5 h-5" />
                Ask about this recipe
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
              
              <div className="md:col-span-1 space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Ingredients</h2>
                <ul className="space-y-4">
                  {recipe.ingredients.map((ing, i) => (
                    <li key={i} className="flex items-start gap-3 text-foreground leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                      <span className="first-letter:uppercase">{ing}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="md:col-span-2 space-y-6">
                <h2 className="text-2xl font-serif font-bold text-foreground">Instructions</h2>
                <div className="space-y-8">
                  {recipe.steps.map((step, i) => (
                    <div key={i} className="flex gap-4">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold font-serif">
                        {i + 1}
                      </div>
                      <p className="text-foreground leading-relaxed pt-1 first-letter:uppercase">
                        {step}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </div>
        )}
      </div>
    </PageShell>
  );
}
