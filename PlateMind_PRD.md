# PlateMind — Project Reference Doc
*AI-powered pantry-first recipe recommender & conversational meal planner*

> Working name: **PlateMind**. Swap freely — alternatives: SousAI, PantryLoop, CookMind, Larder.

This doc is written as a single reference for an agentic coding tool (Antigravity) to build from. It covers: PRD, website/app flow, tech stack, frontend guidelines, backend schema, and a phased implementation plan.

---

## 1. PRD (Product Requirements)

### 1.1 Problem statement
People default to the same 5–10 meals because deciding "what to cook with what I have" is friction-heavy. Existing recipe sites are keyword-search-first, not pantry-first or preference-aware, and don't get smarter about a specific user over time.

### 1.2 Goal
Build a recommender that ranks recipes by (a) how well they match ingredients the user actually has, (b) their taste/dietary profile learned from past interactions, and (c) a conversational layer that lets them refine results in natural language ("make it vegetarian," "under 20 minutes," "swap the cilantro").

### 1.3 Target user
Home cooks who want less decision fatigue — not professional chefs, not a recipe-hoarding/blogging audience.

### 1.4 Core features (MVP)
1. **Pantry input** — add ingredients you have (chips/tags UI), get ranked recipe matches.
2. **Hybrid recommendations** — collaborative filtering + content embeddings + pantry-match score + dietary filters, blended by a learned ranker.
3. **Conversational refinement (RAG chat)** — chat panel that re-ranks/filters current results or answers questions about a recipe ("can I substitute X?").
4. **Recipe detail page** — ingredients, steps, nutrition (if available), save/favorite, "cooked this" tracking.
5. **Personalized weekly meal plan** — auto-generated from saved/cooked history + pantry, editable.
6. **Auth + profile** — dietary preferences, allergies, cuisine preferences, saved recipes, pantry persists across sessions.

### 1.5 Nice-to-have (post-MVP, if time allows)
- Shopping list generated from a meal plan (aggregates missing ingredients).
- "Surprise me" mode using higher exploration weight in the ranker.
- Image-based pantry input (upload a fridge photo → ingredient detection) — stretch goal, separate model.

### 1.6 Explicitly out of scope for MVP
- Social features (following users, public profiles).
- Native mobile app (responsive web only).
- Grocery delivery integration.

### 1.7 Success criteria (portfolio framing)
- Deployed, publicly accessible URL.
- Recommendation quality demonstrably better than a popularity baseline (Precision@10, NDCG@10 reported, mirrors the eval rigor from your coursework).
- RAG chat has a measured hallucination/irrelevance rate on a test set of queries (don't just eyeball it — write the mini eval, it's a strong resume line).
- Clean case-study README: problem → approach → architecture diagram → results → what you'd improve.

---

## 2. Website / App Flow

### 2.1 Primary user journey
```
Landing page
   → Sign up / Log in (or "Try without account" with local-only pantry)
   → Onboarding: pick dietary prefs, allergies, cuisines you like (3 quick steps)
   → Home / Dashboard
        ├─→ Pantry input → Recommended recipes (ranked list/grid)
        │        └─→ Recipe detail → Save / Mark cooked / Chat about this recipe
        ├─→ Chat panel (persistent, collapsible) → refines the current recommendation set
        ├─→ Meal Plan view → weekly grid, drag recipes in/out, regenerate
        └─→ Saved/Favorites
```

### 2.2 Screens list
| Screen | Purpose |
|---|---|
| Landing / marketing page | Value prop, CTA to try/sign up |
| Onboarding (3 steps) | Dietary restrictions, allergies, cuisine preferences |
| Dashboard / Home | Pantry input + recommended recipe grid |
| Recipe detail | Full recipe, substitution chat entry point, save/cook actions |
| Chat (panel, not full page) | Conversational refinement, persists across navigation within a session |
| Meal Plan | Weekly view, editable, "regenerate" action |
| Saved / Favorites | Grid of saved recipes |
| Profile / Settings | Edit preferences, allergies, view cooking history |

### 2.3 Key interaction: pantry → results
1. User adds ingredients (autocomplete tag input, backed by the ingredient table).
2. Frontend calls `/recommend/pantry` with ingredient list + user_id.
3. Backend returns ranked recipes with a `match_reason` field per recipe (e.g. "8/9 ingredients matched, vegetarian ✓") — **surface this in the UI**, it's the difference between a black-box list and a trustworthy one.
4. Chat panel is seeded with this result set as retrieval context; follow-up messages re-query and re-render the grid.

---

## 3. Tech Stack

### Frontend
- **Next.js 14+ (App Router)**, TypeScript
- **Tailwind CSS** + **shadcn/ui** for component primitives
- **Zustand** for lightweight client state (pantry list, chat state)
- **TanStack Query** for server-state/data fetching + caching
- **Framer Motion** for micro-interactions (card entrance, chat panel slide)

### Backend
- **FastAPI** (Python) — REST API, mirrors what you already know from the coursework
- **LangChain** for the RAG chain (retriever + prompt + LLM call)
- **Groq API** (Llama 3.3 70B or 3.1 8B) for the LLM — fast + genuinely free, avoids self-hosting an LLM for a live public demo. (Swap for OpenAI/Anthropic API if preferred; keep it hosted, not self-hosted, for deployability.)
  - **Cost: $0.** No credit card required. Free tier is rate-limited, not metered — roughly 30 requests/min and ~1,000 requests/day per model, at the org level (not per key). More than enough for a portfolio demo; design around the limits, not around a bill.
  - **Design implications of the rate limit:**
    - Debounce/throttle chat input on the frontend so rapid typing doesn't fire a request per keystroke.
    - Cache identical `/recommend/pantry` queries briefly (e.g. 60s in-memory or Redis-free TTL cache) so repeated demo clicks don't burn the daily quota.
    - Add a graceful fallback message ("recommendations are running slow, one sec") if a 429 comes back, rather than a raw error — a portfolio reviewer hitting a rate limit shouldn't see a stack trace.
- **sentence-transformers** (`all-MiniLM-L6-v2`) for recipe embeddings, computed offline during ETL

### Data & ML
- **PostgreSQL** with **pgvector** extension — one database for both relational data *and* vector search (via Supabase, which gives you Postgres + pgvector + auth in one free-tier service — simpler ops than running a separate Chroma/FAISS service)
- **pandas / Polars** for ETL
- **scikit-learn / implicit** for baseline CF + matrix factorization
- **LightGBM** for the hybrid learn-to-rank layer
- **Optuna** for hyperparameter tuning

### Infra / Deployment
- **Frontend:** Vercel
- **Backend:** Render or Railway (FastAPI service)
- **DB + Auth + Vector store:** Supabase
- **CI:** GitHub Actions (lint + test on push, minimum)
- **Cost: $0** across this stack at free-tier usage.
- **Cold starts:** Render/Railway free-tier services sleep after inactivity and take a few seconds to wake on the next request. Design for this explicitly — don't let it read as a bug:
  - Frontend shows a proper loading state (skeleton cards, not a blank screen) on the first request of a session.
  - Optional: a lightweight external cron/uptime ping (e.g. a free UptimeRobot check every ~10 min) keeps the backend warm during active demo periods — mention this as an option, not a requirement.

### Dataset
- **Food.com Recipes and Interactions** (Kaggle) — ~180K recipes, ~700K real user ratings/reviews. Real interaction data (unlike UrbanNest's synthetic data) is a meaningfully stronger portfolio point — say so explicitly in your README.

---

## 4. Frontend Guidelines

### 4.1 Design principles
- **Trust through transparency.** Every recommendation shows *why* (matched ingredients, dietary fit) — never a bare ranked list with no reasoning shown.
- **Food is visual.** Recipe cards are image-forward; don't undersell photography-style imagery with cramped text-heavy cards.
- **Chat augments, doesn't replace.** The chat panel is a refinement tool alongside the grid, not a full-screen takeover — the user should always see results updating live, not just text replies.
- **Low friction pantry input.** Autocomplete + common-ingredient chips beat a blank text field.

### 4.2 Visual direction
- Warm, appetite-appropriate palette (don't default to generic blue SaaS colors) — think warm neutrals + one saturated accent (e.g., a tomato-red or herb-green accent on a warm white/cream base — cream is fine *here* since it's food, unlike a generic app).
- Typography: a clean sans for UI (e.g., Inter) + optionally a warm serif for recipe titles to signal "editorial/food" rather than "dashboard."
- Generous whitespace and card shadows over heavy borders/dividers.
- Avoid: default Bootstrap look, cookie-cutter SaaS gradients, stock-photo hero images.

### 4.3 Component structure (suggested)
```
/components
  /recipe
    RecipeCard.tsx
    RecipeDetail.tsx
    MatchBadge.tsx        (shows "8/9 ingredients" / dietary tags)
  /pantry
    PantryInput.tsx        (tag input w/ autocomplete)
    PantryList.tsx
  /chat
    ChatPanel.tsx
    ChatMessage.tsx
  /mealplan
    WeekGrid.tsx
    MealSlot.tsx
  /ui                       (shadcn primitives)
```

### 4.4 Responsiveness
Mobile-first: pantry input and chat panel are the two components most likely to be used one-handed on mobile — design those first, then scale up to the desktop grid layout.

---

## 5. Backend Schema (PostgreSQL + pgvector)

```sql
-- Users
users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
)

user_preferences (
  user_id UUID REFERENCES users(id) PRIMARY KEY,
  dietary_restrictions TEXT[],       -- e.g. {vegetarian, gluten-free}
  allergies TEXT[],
  cuisine_preferences TEXT[],
  updated_at TIMESTAMPTZ DEFAULT now()
)

-- Recipes (from Food.com dataset, ETL'd)
recipes (
  id INTEGER PRIMARY KEY,            -- source recipe id
  name TEXT NOT NULL,
  description TEXT,
  cuisine TEXT,
  prep_minutes INTEGER,
  cook_minutes INTEGER,
  servings INTEGER,
  image_url TEXT,
  instructions TEXT[],
  nutrition JSONB,                   -- calories, protein, etc. if available
  embedding VECTOR(384),             -- all-MiniLM-L6-v2 output
  created_at TIMESTAMPTZ DEFAULT now()
)

ingredients (
  id SERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  normalized_name TEXT NOT NULL      -- lowercased, singularized, for matching
)

recipe_ingredients (
  recipe_id INTEGER REFERENCES recipes(id),
  ingredient_id INTEGER REFERENCES ingredients(id),
  quantity TEXT,                     -- free text, e.g. "2 cups"
  PRIMARY KEY (recipe_id, ingredient_id)
)

-- User interactions (drives CF + RFM-style features)
user_interactions (
  id SERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  recipe_id INTEGER REFERENCES recipes(id),
  interaction_type TEXT CHECK (interaction_type IN ('viewed','saved','cooked','rated')),
  rating SMALLINT,                   -- nullable, 1-5, only for 'rated'
  created_at TIMESTAMPTZ DEFAULT now()
)

-- Pantry (persists per user)
pantry_items (
  user_id UUID REFERENCES users(id),
  ingredient_id INTEGER REFERENCES ingredients(id),
  added_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (user_id, ingredient_id)
)

-- Meal plans
meal_plans (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  week_start DATE,
  created_at TIMESTAMPTZ DEFAULT now()
)

meal_plan_items (
  meal_plan_id UUID REFERENCES meal_plans(id),
  day_of_week SMALLINT,              -- 0-6
  meal_slot TEXT,                    -- breakfast/lunch/dinner
  recipe_id INTEGER REFERENCES recipes(id),
  PRIMARY KEY (meal_plan_id, day_of_week, meal_slot)
)

-- Chat sessions (for RAG conversational context)
chat_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now()
)

chat_messages (
  id SERIAL PRIMARY KEY,
  session_id UUID REFERENCES chat_sessions(id),
  role TEXT CHECK (role IN ('user','assistant')),
  content TEXT,
  retrieved_recipe_ids INTEGER[],    -- for eval/debugging traceability
  created_at TIMESTAMPTZ DEFAULT now()
)
```

**Index notes:** vector index on `recipes.embedding` (`ivfflat` or `hnsw` via pgvector), plus a GIN index on `ingredients.normalized_name` for fast pantry matching.

### API endpoints (FastAPI)
```
POST   /auth/signup | /auth/login
GET    /recipes/{id}
GET    /recipes/search?q=&cuisine=&max_time=
POST   /recommend/pantry          { user_id, ingredients[] } → ranked recipes + match_reason
POST   /recommend/hybrid          { user_id } → general personalized feed
POST   /chat                      { session_id, message } → RAG response + updated recipe set
GET    /pantry/{user_id}
POST   /pantry/{user_id}          { ingredient }
DELETE /pantry/{user_id}/{ingredient_id}
GET    /favorites/{user_id}
POST   /favorites/{user_id}       { recipe_id }
GET    /mealplan/{user_id}/current
POST   /mealplan/{user_id}/generate
PATCH  /mealplan/{plan_id}/{day}/{slot}   { recipe_id }
```

---

## 6. Implementation Plan (phased, mirrors your coursework structure)

### Phase 0 — Setup (few days)
- Repo scaffold (frontend + backend as separate folders or a monorepo), Supabase project, env config, CI skeleton.
- Wireframe the 8 screens (even rough Figma/Excalidraw) before writing UI code.

### Phase 1 — Data & baseline recommender
- Download + clean Food.com dataset, load into Postgres.
- Build ingredient normalization (this is the trickiest part — "tomato" vs "tomatoes" vs "cherry tomatoes").
- RFM-style user features from real interaction data.
- Baseline models: popularity, user-based CF, item-based CF, matrix factorization (implicit/Surprise).
- Evaluate: Precision@K, Recall@K, coverage — same rigor as your coursework, write it up.

### Phase 2 — Embeddings + hybrid ranker
- Generate recipe embeddings (sentence-transformers), store in pgvector.
- Content-based recommender via vector similarity.
- Pantry-match scoring function (ingredient overlap, weighted by rarity).
- Hybrid ranker: LightGBM combining CF score + embedding similarity + pantry match + dietary filter as a hard constraint (not just a signal — allergies must be a filter, never "soft").
- Optuna tuning, document NDCG@10 improvement over baseline.

### Phase 3 — RAG conversational layer
- LangChain retrieval chain over the pgvector store.
- Prompt templates for: substitution questions, dietary refinement, time constraints.
- Groq LLM integration, test multi-turn context handling.
- Mini eval set (~20-30 test queries) scoring relevance/hallucination — even a manual rubric is fine, just document it.
- Build the rate-limit guardrails now (debounce, short-TTL cache, graceful 429 handling) — cheaper to bake in here than retrofit after the frontend is wired up in Phase 5.

### Phase 4 — Backend API
- FastAPI endpoints per the schema above, wired to the models from Phases 1-3.
- Auth (Supabase Auth), request/response schemas (Pydantic), basic rate limiting.

### Phase 5 — Frontend build
- Design system first (colors, type, spacing — lock this before building screens).
- Build screens in this order: Dashboard/pantry input → Recipe detail → Chat panel → Meal plan → Auth/onboarding → Saved/Profile.
- Wire to live API, replace mocked data incrementally.

### Phase 6 — Deploy + polish
- Deploy frontend (Vercel), backend (Render/Railway), verify env vars/CORS.
- Write the README as a case study: problem, architecture diagram, key metrics, tradeoffs, what you'd do with more time.
- Record a short demo video/GIF for the portfolio page — reviewers often won't click a live link, but will watch 20 seconds.

---

## Notes for Antigravity
- Treat Phase 1-3 (data/ML) as Python-only work independent of the web app; the FastAPI layer in Phase 4 is the seam where ML meets product.
- Keep the `match_reason` / retrieval-traceability fields (in both the recipe recommend response and `chat_messages.retrieved_recipe_ids`) — they're cheap to add now and are what make the eventual demo/case-study credible instead of black-box.
- Dietary restrictions and allergies are hard filters applied *before* ranking, never a ranking signal alone — a mismatch here is a real product bug, not a minor quality issue.
