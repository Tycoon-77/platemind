/**
 * RecipeDetail.tsx
 *
 * Full recipe view: ingredients, instructions, nutrition, save/cooked actions,
 * and an entry point to the chat panel ("Ask about this recipe").
 *
 * Phase 5: wire to GET /recipes/{id} response and POST /favorites/{user_id}.
 */
import type { FC } from "react";

export interface RecipeDetailProps {
  id: number;
  name: string;
  description?: string;
  imageUrl?: string;
  cuisine?: string;
  prepMinutes?: number;
  cookMinutes?: number;
  servings?: number;
  instructions?: string[];
  ingredients?: Array<{ name: string; quantity: string }>;
  nutrition?: Record<string, number | string>;
}

const RecipeDetail: FC<RecipeDetailProps> = ({
  name,
  description,
  imageUrl,
  cuisine,
  prepMinutes,
  cookMinutes,
  servings,
  instructions = [],
  ingredients = [],
}) => {
  // TODO (Phase 5): add save/favorite button wired to POST /favorites/{user_id}.
  // TODO (Phase 5): add "Mark as cooked" button wired to POST /interactions.
  // TODO (Phase 5): surface chat entry point ("Ask about this recipe").

  return (
    <article className="max-w-2xl mx-auto py-8 px-4 space-y-6">
      {/* Hero image */}
      {imageUrl && (
        <div className="rounded-2xl overflow-hidden h-72">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={imageUrl} alt={name} className="object-cover w-full h-full" />
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-stone-900">{name}</h1>
        <div className="flex gap-4 mt-2 text-sm text-stone-500">
          {cuisine && <span>{cuisine}</span>}
          {prepMinutes && <span>Prep: {prepMinutes} min</span>}
          {cookMinutes && <span>Cook: {cookMinutes} min</span>}
          {servings && <span>Serves: {servings}</span>}
        </div>
        {description && <p className="mt-3 text-stone-600">{description}</p>}
      </div>

      {/* Ingredients */}
      {ingredients.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">Ingredients</h2>
          <ul className="space-y-1">
            {ingredients.map((ing) => (
              <li key={ing.name} className="text-stone-700">
                <span className="font-medium">{ing.quantity}</span> {ing.name}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Instructions */}
      {instructions.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold mb-3">Instructions</h2>
          <ol className="space-y-3 list-decimal list-inside">
            {instructions.map((step, i) => (
              <li key={i} className="text-stone-700 leading-relaxed">
                {step}
              </li>
            ))}
          </ol>
        </section>
      )}
    </article>
  );
};

export default RecipeDetail;
