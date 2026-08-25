"use client";

import { useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { useAuthStore } from "@/stores/authStore";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const login = useAuthStore(state => state.login);
  const router = useRouter();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, display_name: displayName, dietary_tags: [], allergies: [] }),
      });
      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || "Signup failed");

      // Auto login after signup
      login(data.access_token, data.user_id, data.email, displayName);
      toast.success("Account created! Let's set up your kitchen.");
      router.push("/onboarding");
    } catch (err: unknown) {
      toast.error((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="max-w-md mx-auto mt-20 p-8 bg-card border border-border rounded-2xl shadow-sm">
        <h1 className="text-3xl font-serif font-bold text-center mb-2 text-foreground">Create Account</h1>
        <p className="text-center text-muted-foreground mb-6">Join PlateMind to save recipes and get personalized recommendations.</p>
        
        <form onSubmit={handleSignup} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Display Name (Optional)</label>
            <input 
              type="text" 
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Email</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-1">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 rounded-xl border border-border bg-background focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>
          <button 
            type="submit" 
            disabled={isLoading}
            className="w-full bg-primary text-primary-foreground py-3 rounded-xl font-bold mt-4 hover:bg-primary/90 transition-all disabled:opacity-70"
          >
            {isLoading ? "Creating Account..." : "Sign Up"}
          </button>
        </form>
        <p className="text-center mt-6 text-sm text-muted-foreground">
          Already have an account? <Link href="/login" className="text-primary font-medium hover:underline">Log in</Link>
        </p>
      </div>
    </PageShell>
  );
}
