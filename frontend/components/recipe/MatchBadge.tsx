/**
 * MatchBadge.tsx
 *
 * Displays pantry-match and dietary-fit signals for a recipe.
 * Always visible — transparency in recommendations is a core product value.
 *
 * Example outputs:
 *   "8/9 ingredients matched"
 *   "vegetarian ✓"
 *   "gluten-free ✓"
 *
 * Phase 5: receive real data from /recommend/pantry `match_reason` field.
 */
import type { FC } from "react";

export interface MatchBadgeProps {
  /** e.g. "8/9 ingredients matched" */
  ingredientMatch?: string;
  /** e.g. ["vegetarian", "gluten-free"] */
  dietaryTags?: string[];
}

const MatchBadge: FC<MatchBadgeProps> = ({ ingredientMatch, dietaryTags = [] }) => {
  if (!ingredientMatch && dietaryTags.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-1.5">
      {ingredientMatch && (
        <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">
          🧺 {ingredientMatch}
        </span>
      )}
      {dietaryTags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800"
        >
          ✓ {tag}
        </span>
      ))}
    </div>
  );
};

export default MatchBadge;
