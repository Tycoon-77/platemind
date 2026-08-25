# PlateMind

> AI-powered pantry-first recipe recommender & conversational meal planner.

PlateMind ranks recipes by how well they match ingredients you actually have, learns your taste profile over time, and lets you refine results through natural-language chat ("make it vegetarian," "under 20 minutes").

---

## Architecture

```
platemind/
├── frontend/     Next.js 14 (App Router) · TypeScript · Tailwind · shadcn/ui
└── backend/      FastAPI · Python · LangChain · Groq · pgvector (Supabase)
```

**Deployment targets (all free-tier):**
| Layer | Service |
|---|---|
| Frontend | Vercel |
| Backend API | Render / Railway |
| Database + Auth + Vectors | Supabase (Postgres + pgvector) |

---

## Prerequisites

| Tool | Min version |
|---|---|
| Node.js | 18+ |
| npm | 9+ |
| Python | 3.9+ |
| Git | any recent |

---

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url> platemind
cd platemind
```

### 2. Frontend

```bash
cd frontend
npm install

# Copy the example env file and fill in your values
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL and Supabase keys
```

### 3. Backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install core dependencies (dev-only install — ML deps added in Phase 1)
pip install fastapi uvicorn pydantic pydantic-settings python-dotenv

# Copy the example env file and fill in your values
cp .env.example .env
# Edit .env — set Supabase URL/keys and Groq API key
```

---

## Running Dev Servers

Open **two terminal windows** from the repo root:

**Terminal 1 — Frontend:**
```bash
cd frontend
npm run dev
# → http://localhost:3000
```

**Terminal 2 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000
# → Swagger UI: http://localhost:8000/docs
```

---

## Project Structure

### Frontend (`/frontend`)

```
app/                   Next.js App Router pages and layouts
components/
  recipe/
    RecipeCard.tsx     Image-forward card with match badge
    RecipeDetail.tsx   Full recipe view (ingredients, steps, nutrition)
    MatchBadge.tsx     "8/9 ingredients matched · vegetarian ✓"
  pantry/
    PantryInput.tsx    Tag input with autocomplete
    PantryList.tsx     Persisted pantry items display
  chat/
    ChatPanel.tsx      Collapsible slide-in conversational panel
    ChatMessage.tsx    Individual message bubble
  mealplan/
    WeekGrid.tsx       7×3 weekly meal plan grid
    MealSlot.tsx       Individual day+meal slot cell
  ui/                  shadcn/ui primitives (auto-generated)
stores/
  pantryStore.ts       Zustand: client-side pantry state
  chatStore.ts         Zustand: chat session + panel state
```

### Backend (`/backend`)

```
app/
  main.py             FastAPI app + CORS + router registration
  config.py           Typed env-var settings (pydantic-settings)
  routers/
    auth.py           POST /auth/signup | /auth/login
    recipes.py        GET  /recipes/{id} | /recipes/search
    recommend.py      POST /recommend/pantry | /recommend/hybrid
    chat.py           POST /chat
    pantry.py         GET|POST|DELETE /pantry/{user_id}
    favorites.py      GET|POST /favorites/{user_id}
    mealplan.py       GET|POST|PATCH /mealplan/...
  schemas/            Pydantic request/response models (Phase 4)
  services/           Business logic layer (Phase 4)
  models/             SQLAlchemy ORM models (Phase 4)
```

---

## API Reference

Full interactive docs at **http://localhost:8000/docs** (Swagger UI) when the backend is running.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/signup` | Create account |
| POST | `/auth/login` | Log in → JWT |
| GET | `/recipes/{id}` | Recipe detail |
| GET | `/recipes/search` | Search by keyword/cuisine/time |
| POST | `/recommend/pantry` | Ranked recipes from pantry ingredients |
| POST | `/recommend/hybrid` | Personalised feed |
| POST | `/chat` | RAG conversational refinement |
| GET | `/pantry/{user_id}` | Fetch pantry |
| POST | `/pantry/{user_id}` | Add ingredient |
| DELETE | `/pantry/{user_id}/{ingredient_id}` | Remove ingredient |
| GET | `/favorites/{user_id}` | Saved recipes |
| POST | `/favorites/{user_id}` | Save recipe |
| GET | `/mealplan/{user_id}/current` | Current week's plan |
| POST | `/mealplan/{user_id}/generate` | Auto-generate plan |
| PATCH | `/mealplan/{plan_id}/{day}/{slot}` | Update meal slot |
| GET | `/health` | Liveness check |

---

## Implementation Phases

| Phase | Focus | Status |
|---|---|---|
| **0 — Setup** | Monorepo scaffold, route stubs, env config | ✅ Done |
| **1 — Data & Baseline** | Food.com ETL, Postgres schema, baseline CF | ⏳ Next |
| **2 — Embeddings & Ranker** | pgvector embeddings, LightGBM hybrid ranker | ⏳ |
| **3 — RAG Chat** | LangChain + Groq, rate-limit guardrails, eval | ⏳ |
| **4 — Backend API** | Wire models to FastAPI, Supabase Auth, Pydantic | ⏳ |
| **5 — Frontend** | Full UI, TanStack Query, live API wiring | ⏳ |
| **6 — Deploy & Polish** | Vercel + Render, README case study, demo video | ⏳ |

---

## Environment Variables

### Frontend (`frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key (safe for browser) |

### Backend (`backend/.env`)

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key (server-side only — keep secret) |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg format) |
| `GROQ_API_KEY` | Groq API key ([console.groq.com](https://console.groq.com)) |
| `GROQ_MODEL` | Model ID (default: `llama-3.3-70b-versatile`) |
| `ENVIRONMENT` | `development` or `production` |
| `CORS_ORIGINS` | Comma-separated allowed origins |

---

## Contributing

This is a personal portfolio project. Issues and PRs welcome — see `AGENTS.md` for AI agent guidance.
