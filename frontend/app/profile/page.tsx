/* eslint-disable */
"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { UserIcon, CheckCircleIcon, SettingsIcon } from "lucide-react";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

const DIETARY_OPTIONS = ["Vegan", "Vegetarian", "Pescatarian", "Paleo", "Keto", "Gluten-Free"];
const ALLERGY_OPTIONS = ["Dairy", "Peanuts", "Tree Nuts", "Eggs", "Shellfish", "Soy"];

export default function ProfilePage() {
  const { userId, token, email, displayName, logout } = useAuthStore();
  const router = useRouter();

  const [dietary, setDietary] = useState<string[]>([]);
  const [allergies, setAllergies] = useState<string[]>([]);
  const [cooked, setCooked] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!userId || !token) {
      router.push("/login");
      return;
    }

    const fetchData = async () => {
      try {
        const [prefRes, cookedRes] = await Promise.all([
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/preferences/${userId}`),
          fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/favorites/${userId}/cooked`, { headers: { "Authorization": `Bearer ${token}` } })
        ]);

        if (prefRes.ok) {
          const prefData = await prefRes.json();
          setDietary(prefData.dietary_tags || []);
          setAllergies(prefData.allergies || []);
        }

        if (cookedRes.ok) {
          const cookedData = await cookedRes.json();
          setCooked(cookedData.cooked || []);
        }
      } catch (err) {
        toast.error("Failed to load profile data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [userId, token, router]);

  const toggleSelection = (item: string, list: string[], setList: (l: string[]) => void) => {
    if (list.includes(item)) setList(list.filter(i => i !== item));
    else setList([...list, item]);
  };

  const handleSavePreferences = async () => {
    setIsSaving(true);
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

      
      if (res.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) throw new Error("Failed to update preferences");
      toast.success("Preferences updated successfully!");
    } catch (err: unknown) {
      toast.error((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  if (!userId) return null; // Let the useEffect redirect

  return (
    <PageShell>
      <div className="max-w-5xl mx-auto space-y-10 py-6 animate-in fade-in slide-in-from-bottom-4">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-border pb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-primary-foreground font-serif text-3xl font-bold">
              {displayName ? displayName.charAt(0).toUpperCase() : email?.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-3xl font-serif font-bold text-foreground">
                {displayName || "Your Profile"}
              </h1>
              <p className="text-muted-foreground">{email}</p>
            </div>
          </div>
          <button 
            onClick={() => { logout(); router.push("/"); }}
            className="text-sm font-medium text-destructive hover:bg-destructive/10 px-4 py-2 rounded-full transition-colors"
          >
            Log out
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
          {/* Settings Section */}
          <div className="space-y-6">
            <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
              <SettingsIcon className="w-6 h-6 text-primary" />
              Preferences
            </h2>
            
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-24 w-full rounded-xl" />
                <Skeleton className="h-24 w-full rounded-xl" />
              </div>
            ) : (
              <div className="bg-card border border-border p-6 rounded-2xl shadow-sm space-y-8">
                
                <div className="space-y-3">
                  <label className="font-semibold text-foreground">Dietary Restrictions</label>
                  <div className="flex flex-wrap gap-2">
                    {DIETARY_OPTIONS.map(diet => (
                      <button
                        key={diet}
                        onClick={() => toggleSelection(diet, dietary, setDietary)}
                        className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
                          dietary.includes(diet) 
                            ? "bg-primary border-primary text-primary-foreground" 
                            : "bg-background border-border text-foreground hover:border-primary/50"
                        }`}
                      >
                        {diet}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <label className="font-semibold text-foreground">Allergies</label>
                  <div className="flex flex-wrap gap-2">
                    {ALLERGY_OPTIONS.map(allergy => (
                      <button
                        key={allergy}
                        onClick={() => toggleSelection(allergy, allergies, setAllergies)}
                        className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all border ${
                          allergies.includes(allergy) 
                            ? "bg-destructive border-destructive text-destructive-foreground" 
                            : "bg-background border-border text-foreground hover:border-destructive/50"
                        }`}
                      >
                        {allergy}
                      </button>
                    ))}
                  </div>
                </div>

                <button 
                  onClick={handleSavePreferences}
                  disabled={isSaving}
                  className="w-full bg-primary text-primary-foreground py-2.5 rounded-xl font-bold hover:bg-primary/90 transition-all disabled:opacity-70"
                >
                  {isSaving ? "Saving..." : "Save Preferences"}
                </button>
              </div>
            )}
          </div>

          {/* Cooking History Section */}
          <div className="space-y-6">
            <h2 className="text-2xl font-serif font-bold flex items-center gap-2">
              <CheckCircleIcon className="w-6 h-6 text-primary" />
              Cooking History
            </h2>
            
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-16 w-full rounded-xl" />
                <Skeleton className="h-16 w-full rounded-xl" />
              </div>
            ) : cooked.length === 0 ? (
              <div className="bg-card border border-dashed border-border p-8 rounded-2xl text-center">
                <p className="text-muted-foreground mb-4">You haven&apos;t marked any recipes as cooked yet.</p>
                <Link href="/" className="text-primary font-medium hover:underline">
                  Find a recipe to cook
                </Link>
              </div>
            ) : (
              <div className="bg-card border border-border rounded-2xl shadow-sm overflow-hidden">
                {cooked.map((c, i) => (
                  <Link 
                    key={`${c.recipe_id}-${i}`}
                    href={`/recipes/${c.recipe_id}`}
                    className={`flex items-center justify-between p-4 hover:bg-secondary/50 transition-colors ${i !== cooked.length - 1 ? 'border-b border-border' : ''}`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                      <p className="font-medium capitalize text-foreground">{c.name}</p>
                    </div>
                    <p className="text-sm text-muted-foreground">{c.minutes} mins</p>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
