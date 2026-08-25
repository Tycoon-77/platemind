import re
path = "frontend/components/layout/PageShell.tsx"
with open(path, "r") as f:
    text = f.read()

replacement = """      <div className="container mx-auto px-4 h-16 relative flex items-center justify-between">
        
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
        
        <div className="flex-1 flex justify-end items-center gap-4">"""

text = re.sub(
    r'<div className="container mx-auto px-4 h-16 flex items-center justify-between">[\s\S]*?<div className="flex items-center gap-4">',
    replacement,
    text
)

with open(path, "w") as f:
    f.write(text)
