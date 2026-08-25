/* eslint-disable */

"use client";

import { useEffect, useState, useCallback } from "react";
import { PageShell } from "@/components/layout/PageShell";
import WeekGrid, { MealPlanData, SlotKey } from "@/components/mealplan/WeekGrid";
import { useAuthStore } from "@/stores/authStore";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import Link from "next/link";
import { CalendarIcon, ChefHatIcon, RefreshCcwIcon } from "lucide-react";

export default function MealPlanPage() {
  const { token, userId } = useAuthStore();
  const [mealPlanData, setMealPlanData] = useState<MealPlanData | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [swapModalOpen, setSwapModalOpen] = useState(false);
  const [swapTarget, setSwapTarget] = useState<{day: number, slot: string} | null>(null);
  const [swapCandidates, setSwapCandidates] = useState<Record<string, unknown>[]>([]);
  const [isSwapping, setIsSwapping] = useState(false);

  const fetchPlan = useCallback(async () => {
    if (!userId || !token) {
      setIsLoading(false);
      return;
    }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/mealplan/${userId}/current`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to fetch plan");
      
      const data = await res.json();
      if (data.meal_plan) {
        setPlanId(data.meal_plan.plan_id);
        const formattedData: Partial<MealPlanData> = {};
        data.meal_plan.slots.forEach((s: Record<string, unknown>) => {
          const key: SlotKey = `${s.day}-${s.slot}` as SlotKey;
          formattedData[key] = { id: s.recipe_id as number, name: s.name as string };
        });
        setMealPlanData(formattedData as MealPlanData);
      } else {
        setMealPlanData(null);
      }
    } catch (err: unknown) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [userId, token]);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/mealplan/${userId}/generate`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to generate plan");
      }
      toast.success("Meal plan generated successfully!");
      await fetchPlan();
    } catch (err: unknown) {
      toast.error((err as Error).message);
    } finally {
      setIsGenerating(false);
    }
  };

  const openSwapModal = async (day: number, slot: string) => {
    setSwapTarget({ day, slot });
    setSwapModalOpen(true);
    setIsSwapping(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recipes/search?max_time=45`);
      const data = await res.json();
      const random = data.results.sort(() => 0.5 - Math.random()).slice(0, 5);
      setSwapCandidates(random);
    } catch (err: unknown) {
      console.error(err);
      toast.error("Failed to load swap candidates");
    } finally {
      setIsSwapping(false);
    }
  };

  const executeSwap = async (recipeId: number) => {
    if (!planId || !swapTarget || !token) return;
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/mealplan/${planId}/${swapTarget.day}/${swapTarget.slot}`, {
        method: "PATCH",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ recipe_id: recipeId })
      });
      
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to update slot");
      toast.success("Meal updated!");
      setSwapModalOpen(false);
      await fetchPlan();
    } catch (err: unknown) {
      toast.error((err as Error).message);
    }
  };

  if (!userId) {
    return (
      <PageShell>
        <div className="max-w-xl mx-auto py-20 text-center space-y-6">
          <CalendarIcon className="w-16 h-16 mx-auto text-primary opacity-50" />
          <h1 className="text-3xl font-serif font-bold text-foreground">Your Weekly Meal Plan</h1>
          <p className="text-muted-foreground text-lg">Sign up to build a personalized meal plan based on your tastes, pantry, and dietary needs.</p>
          <div className="pt-6">
            <Link href="/signup" className="bg-primary text-primary-foreground px-8 py-3 rounded-full font-bold shadow-sm hover:bg-primary/90 transition-all text-lg">
              Sign up to build a meal plan
            </Link>
          </div>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="max-w-6xl mx-auto space-y-10 py-6 animate-in fade-in slide-in-from-bottom-4">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border pb-6">
          <div className="space-y-1">
            <h1 className="text-3xl font-serif font-bold text-foreground flex items-center gap-2">
              <CalendarIcon className="w-7 h-7 text-primary" />
              Weekly Meal Plan
            </h1>
            <p className="text-muted-foreground">Tailored to your dietary preferences and tastes.</p>
          </div>
          
          <button 
            onClick={handleGenerate}
            disabled={isGenerating}
            className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2.5 rounded-full font-bold hover:bg-primary/90 transition-all shadow-sm disabled:opacity-70"
          >
            <RefreshCcwIcon className={`w-4 h-4 ${isGenerating ? 'animate-spin' : ''}`} />
            {isGenerating ? "Generating..." : (mealPlanData ? "Regenerate Plan" : "Generate Plan")}
          </button>
        </div>

        {isLoading || isGenerating ? (
          <div className="space-y-4">
            <Skeleton className="h-10 w-full rounded-xl" />
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-24 w-full rounded-xl" />
          </div>
        ) : !mealPlanData ? (
          <div className="text-center py-24 bg-card border border-dashed border-border rounded-2xl">
            <ChefHatIcon className="w-16 h-16 mx-auto text-muted-foreground opacity-30 mb-4" />
            <h2 className="text-2xl font-serif font-bold text-foreground mb-2">No plan for this week</h2>
            <p className="text-muted-foreground mb-6">Let PlateMind generate a personalized menu for you.</p>
            <button 
              onClick={handleGenerate}
              className="bg-primary text-primary-foreground px-8 py-3 rounded-full font-bold shadow-sm hover:bg-primary/90 transition-all"
            >
              Generate My Meal Plan
            </button>
          </div>
        ) : (
          <div className="bg-card border border-border rounded-2xl shadow-sm p-4 md:p-6 overflow-hidden">
            <WeekGrid mealPlan={mealPlanData} onSlotSwap={openSwapModal} />
          </div>
        )}

      </div>

      {swapModalOpen && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border shadow-xl rounded-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-4 border-b border-border flex justify-between items-center bg-secondary/30">
              <h3 className="font-serif font-bold text-lg">Swap Meal</h3>
              <button onClick={() => setSwapModalOpen(false)} className="text-muted-foreground hover:text-foreground text-xl font-bold px-2">&times;</button>
            </div>
            <div className="p-4 max-h-[60vh] overflow-y-auto space-y-3">
              {isSwapping ? (
                <div className="space-y-3">
                  <Skeleton className="h-16 w-full rounded-xl" />
                  <Skeleton className="h-16 w-full rounded-xl" />
                  <Skeleton className="h-16 w-full rounded-xl" />
                </div>
              ) : (
                swapCandidates.map((c) => (
                  <div key={c.recipe_id as number} onClick={() => executeSwap(c.recipe_id as number)} className="flex items-center gap-3 p-3 border border-border rounded-xl cursor-pointer hover:border-primary hover:bg-secondary/50 transition-all">
                    <div className="flex-1">
                      <p className="font-medium text-sm capitalize line-clamp-1">{c.name as string}</p>
                      <p className="text-xs text-muted-foreground mt-1">{c.minutes as number} mins • {(c.tags as string[])?.find((t: string) => t.includes('cuisine') || t.includes('american') || t.includes('italian')) || 'Mixed'}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

    </PageShell>
  );
}
