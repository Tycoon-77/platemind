/**
 * PantryList.tsx
 *
 * Displays the user's currently saved pantry items (persisted across sessions).
 * Shown separately from the search input — this is the user's "fridge at a glance."
 *
 * Phase 5: wire to GET /pantry/{user_id} via TanStack Query.
 *          DELETE /pantry/{user_id}/{ingredient_id} on remove.
 */
"use client";

export interface PantryItem {
  ingredient_id: number;
  name: string;
}

export interface PantryListProps {
  items: PantryItem[];
  onRemove?: (ingredientId: number) => void;
}

const PantryList = ({ items, onRemove }: PantryListProps) => {
  if (items.length === 0) {
    return (
      <p className="text-sm text-stone-400 italic">
        Your pantry is empty — add ingredients above to get recommendations.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item.ingredient_id}
          className="inline-flex items-center gap-1.5 rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-700"
        >
          {item.name}
          {onRemove && (
            <button
              onClick={() => onRemove(item.ingredient_id)}
              className="text-stone-400 hover:text-red-500 transition-colors leading-none"
              aria-label={`Remove ${item.name} from pantry`}
            >
              ×
            </button>
          )}
        </span>
      ))}
    </div>
  );
};

export default PantryList;
