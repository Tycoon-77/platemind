import React from 'react';
import Link from 'next/link';
import ChatPanel from "@/components/chat/ChatPanel";
import { useAuthStore } from "@/stores/authStore";

export function Navbar() {
  const { token, email, displayName, logout } = useAuthStore();

  return (
    <header className="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 relative flex items-center justify-between">
        
        <div className="flex-1 flex justify-start">
          <Link href="/" className="font-serif text-2xl font-bold text-primary tracking-tight">
            PlateMind
          </Link>
        </div>

        <nav className="hidden md:flex absolute left-1/2 -translate-x-1/2 items-center gap-6 text-sm font-medium">
          <Link href="/" className="text-muted-foreground hover:text-foreground transition-colors">
            Dashboard
          </Link>
          <Link href="/mealplan" className="text-muted-foreground hover:text-foreground transition-colors">
            Meal Plan
          </Link>
          <Link href="/saved" className="text-muted-foreground hover:text-foreground transition-colors">
            Saved Recipes
          </Link>
        </nav>
        
        <div className="flex-1 flex justify-end items-center gap-4">
          {token ? (
            <div className="flex items-center gap-4 group relative">
              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center text-secondary-foreground font-semibold cursor-pointer border border-border">
                {displayName ? displayName.charAt(0).toUpperCase() : email?.charAt(0).toUpperCase()}
              </div>
              
              <div className="absolute top-10 right-0 w-48 bg-card border border-border rounded-xl shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 py-2">
                <div className="px-4 py-2 border-b border-border mb-2">
                  <p className="text-sm font-medium truncate">{displayName || email}</p>
                </div>
                <button 
                  onClick={logout}
                  className="w-full text-left px-4 py-2 text-sm text-destructive hover:bg-secondary/50 transition-colors"
                >
                  Log out
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Log in
              </Link>
              <Link href="/signup" className="text-sm font-medium bg-primary text-primary-foreground px-4 py-2 rounded-full hover:bg-primary/90 transition-colors">
                Sign up
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export function PageShell({ children, onRecipesUpdated }: { children: React.ReactNode, onRecipesUpdated?: (recipes: Record<string, unknown>[]) => void }) {
  return (
    <div className="min-h-screen bg-background flex flex-col font-sans text-foreground relative">
      <Navbar />
      <main className="flex-1 container mx-auto px-4 py-8">
        {children}
      </main>
      <ChatPanel onRecipesUpdated={onRecipesUpdated} />
    </div>
  );
}
