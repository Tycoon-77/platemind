import type { FC } from "react";
import Link from "next/link";
import { RefreshCcwIcon } from "lucide-react";

export interface MealSlotProps {
  recipe?: {
    id: number;
    name: string;
    imageUrl?: string;
  };
  onSwapClick?: () => void;
}

const MealSlot: FC<MealSlotProps> = ({ recipe, onSwapClick }) => {
  if (!recipe) {
    return (
      <div className="rounded-xl border-2 border-dashed border-border h-24 flex items-center justify-center text-muted-foreground bg-background opacity-50">
        Empty
      </div>
    );
  }

  return (
    <div className="group relative rounded-xl bg-card border border-border h-24 flex items-center px-3 gap-3 hover:border-primary/50 transition-all shadow-sm overflow-hidden">
      <Link href={`/recipes/${recipe.id}`} className="absolute inset-0 z-0" aria-label={`View ${recipe.name}`} />
      
      {true && (
        <img
          src={recipe.imageUrl || `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recipes/${recipe.id}/image`}
          onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=80"; }} alt={recipe.name}
          className="w-14 h-14 rounded-lg object-cover flex-shrink-0 z-10 pointer-events-none"
        />
      )}
      
      <p className="text-sm font-serif font-medium text-foreground line-clamp-3 leading-snug z-10 pointer-events-none capitalize">
        {recipe.name}
      </p>

      {/* Hover action to swap */}
      {onSwapClick && (
        <button 
          onClick={(e) => { e.preventDefault(); e.stopPropagation(); onSwapClick(); }}
          className="absolute top-2 right-2 z-20 bg-background border border-border text-foreground hover:text-primary hover:border-primary rounded-full p-1.5 opacity-0 group-hover:opacity-100 transition-all shadow-sm"
          title="Swap Recipe"
        >
          <RefreshCcwIcon className="w-3 h-3" />
        </button>
      )}
    </div>
  );
};

export default MealSlot;
