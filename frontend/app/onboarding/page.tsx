"use client";

import { useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { ChefHatIcon } from "lucide-react";

const DIETARY_OPTIONS = ["Vegan", "Vegetarian", "Pescatarian", "Paleo", "Keto", "Gluten-Free"];
const ALLERGY_OPTIONS = ["Dairy", "Peanuts", "Tree Nuts", "Eggs", "Shellfish", "Soy"];

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const [dietary, setDietary] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const { userId, token } = useAuthStore();
  const router = useRouter();

  const toggleSelection = (item: string, list: string[], setList: (l: string[]) => void) => {
    if (list.includes(item)) setList(list.filter(i => i !== item));
    else setList([...list, item]);
  };

  const handleComplete = async () => {
    if (!userId) {
      toast.error("Not logged in");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/preferences`, {
        method: "PUT",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          dietary_tags: dietary,
          allergies: allergies
        }),
      });

      if (!res.ok) throw new Error("Failed to save preferences");
      
      toast.success("Profile setup complete!");
      router.push("/");
    } catch (err: unknown) {
      toast.error((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="max-w-2xl mx-auto mt-10 p-8 bg-card border border-border rounded-2xl shadow-sm animate-in fade-in slide-in-from-bottom-4">
        
        <div className="flex justify-center mb-6 text-primary">
          <ChefHatIcon className="w-12 h-12" />
        </div>
        
        <h1 className="text-3xl font-serif font-bold text-center mb-2 text-foreground">
          {step === 1 ? "Any dietary restrictions?" : step === 2 ? "Any allergies?" : "You're all set!"}
        </h1>
        <p className="text-center text-muted-foreground mb-8">
          {step === 1 ? "Select any diets you follow. We'll prioritize matching recipes." : 
           step === 2 ? "Select ingredients you need to avoid." : 
           "We'll use this to recommend perfect meals."}
        </p>

        {step === 1 && (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-3 justify-center">
              {DIETARY_OPTIONS.map(diet => (
                <button
                  key={diet}
                  onClick={() => toggleSelection(diet, dietary, setDietary)}
                  className={`px-5 py-2.5 rounded-full font-medium transition-all border ${
                    dietary.includes(diet) 
                      ? "bg-primary border-primary text-primary-foreground shadow-sm" 
                      : "bg-background border-border text-foreground hover:border-primary/50"
                  }`}
                >
                  {diet}
                </button>
              ))}
            </div>
            <button 
              onClick={() => setStep(2)}
              className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold mt-8 hover:bg-primary/90 transition-all"
            >
              Continue
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div className="flex flex-wrap gap-3 justify-center">
              {ALLERGY_OPTIONS.map(allergy => (
                <button
                  key={allergy}
                  onClick={() => toggleSelection(allergy, allergies, setAllergies)}
                  className={`px-5 py-2.5 rounded-full font-medium transition-all border ${
                    allergies.includes(allergy) 
                      ? "bg-destructive border-destructive text-destructive-foreground shadow-sm" 
                      : "bg-background border-border text-foreground hover:border-destructive/50"
                  }`}
                >
                  {allergy}
                </button>
              ))}
            </div>
            <div className="flex gap-4 mt-8">
              <button 
                onClick={() => setStep(1)}
                className="w-1/3 bg-secondary text-secondary-foreground py-3 rounded-xl font-bold hover:bg-secondary/80 transition-all"
              >
                Back
              </button>
              <button 
                onClick={() => setStep(3)}
                className="w-2/3 bg-primary text-primary-foreground py-3 rounded-xl font-bold hover:bg-primary/90 transition-all"
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6 text-center">
            <div className="p-6 bg-secondary/50 rounded-xl inline-block mb-4">
              <p className="font-medium text-foreground">Dietary: <span className="text-primary">{dietary.length ? dietary.join(", ") : "None"}</span></p>
              <p className="font-medium text-foreground mt-2">Allergies: <span className="text-destructive">{allergies.length ? allergies.join(", ") : "None"}</span></p>
            </div>
            <div className="flex gap-4">
              <button 
                onClick={() => setStep(2)}
                className="w-1/3 bg-secondary text-secondary-foreground py-3 rounded-xl font-bold hover:bg-secondary/80 transition-all"
                disabled={isLoading}
              >
                Back
              </button>
              <button 
                onClick={handleComplete}
                disabled={isLoading}
                className="w-2/3 bg-primary text-primary-foreground py-3 rounded-xl font-bold hover:bg-primary/90 transition-all disabled:opacity-70 flex justify-center items-center gap-2"
              >
                {isLoading ? "Saving..." : "Start Exploring"}
              </button>
            </div>
          </div>
        )}

      </div>
    </PageShell>
  );
}
