import type { FC } from "react";
import Link from "next/link";
import { ClockIcon, ChefHatIcon } from "lucide-react";

export interface RecipeCardProps {
  id: number;
  name: string;
  imageUrl?: string;
  cuisine?: string;
  totalMinutes?: number;
  matchReason?: string;
}

const RecipeCard: FC<RecipeCardProps> = ({
  id,
  name,
  imageUrl,
  cuisine,
  totalMinutes,
  matchReason,
}) => {
  return (
    <Link href={`/recipes/${id}`} className="group rounded-xl overflow-hidden bg-card border border-border shadow-sm hover:shadow-md hover:border-primary/20 transition-all duration-300 flex flex-col">
      {/* Recipe image placeholder */}
      <div className="h-48 bg-muted flex items-center justify-center text-4xl relative overflow-hidden">
        {true ? (
          <img src={imageUrl || `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/recipes/${id}/image`} onError={(e) => { e.currentTarget.onerror = null; e.currentTarget.src = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=80"; }} alt={name} className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-500" />
        ) : (
          "🍽️"
        )}
      </div>

      {/* Card body */}
      <div className="p-5 flex flex-col flex-1 gap-3">
        <h3 className="font-serif text-xl font-bold leading-snug line-clamp-2 text-foreground group-hover:text-primary transition-colors capitalize">
          {name}
        </h3>

        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-auto">
          {totalMinutes && (
            <div className="flex items-center gap-1.5">
              <ClockIcon className="w-4 h-4" />
              <span>{totalMinutes} min</span>
            </div>
          )}
          {cuisine && (
            <div className="flex items-center gap-1.5">
              <ChefHatIcon className="w-4 h-4" />
              <span>{cuisine}</span>
            </div>
          )}
        </div>

        {/* Match reason badge */}
        {matchReason && (
          <div className="pt-2 mt-1 border-t border-border">
            <p className="text-xs font-medium text-primary bg-primary/5 rounded-md px-2.5 py-1.5 leading-relaxed inline-block">
              ✨ {matchReason}
            </p>
          </div>
        )}
      </div>
    </Link>
  );
};

export default RecipeCard;
