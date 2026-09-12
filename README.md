# PlateMind

**A pantry-first recipe recommender with conversational refinement — hybrid recommendation engine (collaborative filtering + content embeddings) plus a RAG-based chat layer for natural-language recipe search.**

🔗 **Live demo:** [platemind.vercel.app](https://platemind.vercel.app)
📦 **Repo:** [github.com/Tycoon-77/platemind](https://github.com/Tycoon-77/platemind)

---

## The problem

Recipe sites are keyword-search-first, not pantry-first. You end up filtering by "chicken" and scrolling, rather than getting recipes ranked by what you actually have on hand, what you tend to cook, and your dietary constraints. PlateMind flips that: you tell it your pantry, it ranks recipes by ingredient match, learned taste preferences, and dietary fit — and you can refine the results conversationally ("make it vegetarian," "under 20 minutes," "what can I sub for buttermilk?").

## What it does

<!-- Add your screenshot or GIF here! Example: ![PlateMind Demo](frontend/public/demo.gif) -->

- **Pantry-based recommendations** — type in what you have, get ranked recipes with a visible `match_reason` ("matches 8/9 ingredients, vegetarian ✓") rather than a black-box list.
- **Conversational refinement (RAG)** — a chat panel that re-ranks the current result set or answers substitution questions, backed by retrieval over a vector store, not just a generic LLM call.
- **Hybrid ranking** — combines collaborative filtering, content embeddings, and pantry-match scoring via a trained LightGBM ranker, with dietary restrictions and allergies enforced as hard filters, never a soft ranking signal.
- **Auto-generated weekly meal plans** — a 21-slot week built from your interaction history and preferences, with manual override per slot.
- **Full auth, favorites, and cooking history**, all backed by real Postgres, not mocked data.

## Why this exists

This started as a variation on a bootcamp project (UrbanNest) whose deliverable was a Streamlit/Gradio dashboard on synthetic furniture data. I rebuilt the entire ML pipeline from scratch on a real dataset (Food.com's recipes/interactions, real user ratings) in a different domain, and replaced the dashboard with an actual deployed product with a designed frontend — to have something that demonstrates product thinking and deployment experience, not just a notebook.

---

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Next.js    │─────▶│     FastAPI       │─────▶│   Supabase       │
│   (Vercel)   │◀─────│    (Railway)      │◀─────│ Postgres+pgvector│
└─────────────┘      └──────────────────┘      └─────────────────┘
                             │
                             ▼
                      ┌──────────────┐
                      │  Groq API     │
                      │ (Llama 3.3)   │
                      └──────────────┘
```

**Recommendation pipeline:** Popularity / User-CF / Item-CF / Matrix Factorization baselines → sentence-transformer embeddings + pgvector similarity → TF-IDF-weighted pantry matching → LightGBM hybrid ranker (tuned via Optuna) → dietary hard-filter applied pre-ranking.

**Chat pipeline:** intent classification (GENERAL / REFINE / SUBS) → query rewriting for follow-up turns (fuses prior context into the retrieval query, since raw follow-ups like "make it vegetarian" retrieve poorly in isolation) → pgvector retrieval → Groq LLM generation with an intent-aware grounding prompt (strict recipe-context grounding for GENERAL/REFINE, permits general culinary knowledge for SUBS).

## Tech stack

**Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui, Zustand, Framer Motion
**Backend:** FastAPI, SQLAlchemy, LangChain
**ML/Data:** scikit-learn, `implicit` (ALS), LightGBM, Optuna, sentence-transformers, pandas
**Data store:** Supabase (Postgres + pgvector), SQLite for the read-heavy recipe catalog (see [Deployment challenges](#deployment-challenges))
**LLM:** Groq (Llama 3.3 70B / 3.1 8B) — chosen for a genuinely free tier suitable for a live demo, avoiding the reliability tradeoffs of self-hosting a model behind a public URL
**Hosting:** Vercel (frontend), Railway (backend, Docker), Supabase (DB)

---

## Model evaluation

Real numbers, not cherry-picked. Baselines evaluated with leave-one-out per-user testing on real Food.com interaction data (89K+ recipes):

| Model | Precision@10 | Recall@10 | Coverage |
|---|---|---|---|
| Popularity | 0.0006 | 0.0060 | 0.0002 |
| User-based CF | 0.0017 | 0.0166 | 0.0280 |
| Item-based CF | 0.0014 | 0.0145 | 0.0392 |
| Matrix Factorization (ALS) | 0.0021 | 0.0207 | 0.0111 |
| **Hybrid (LightGBM)** | — | — | **NDCG@10: 0.4852** (vs. 0.3454 for the ALS baseline alone) |

Precision@10 in the 0.001-0.002 range looks low in isolation, but the theoretical ceiling under leave-one-out evaluation on a catalog this size is ~0.1 (one correct answer possible out of 89K+ items) — reported here with that ceiling stated explicitly rather than left to look worse (or better) than it is. Matrix Factorization has the best precision/recall but the lowest coverage of the baselines, meaning it leans on popular items more than the CF approaches — a real tradeoff, not a free win.

### RAG chat evaluation

The first version of this eval was a false 100% — it checked whether retrieval returned *any* non-empty result and whether the reply contained quoted text matching a recipe name, which is a smoke test, not a quality measure. Rebuilt with:
- **Retrieval relevance:** manually-labeled ground-truth recipe IDs per test query, scored as exact hit/miss (strict, not lenient).
- **Hallucination:** LLM-as-judge scoring, made **intent-aware** after discovering the first version penalized legitimate culinary knowledge — substitution questions ("can I use olive oil instead of butter?") inherently require reasoning beyond what's in a retrieved recipe's ingredient list, so GENERAL/REFINE queries are judged on strict grounding while SUBS queries are judged only on whether *recipe-specific* claims are accurate.

Final results (25 test queries):

| Intent | Retrieval | Hallucination-free |
|---|---|---|
| GENERAL | 100% | 90% |
| REFINE | 0%* | 75% |
| SUBS | 0%* | 42% |

*REFINE/SUBS retrieval was tested with isolated queries lacking conversational history — a test-harness gap, not a confirmed product bug, though a query-rewriting fix (fusing prior turns before embedding) didn't move the number, likely due to strict single-ID ground truth on a subset catalog. Documented as a known limitation rather than resolved with more fixes than the finding could support.

SUBS hallucination at 42% is the weakest real number here — substitution answers most often introduce claims not traceable to retrieved context, which is expected given they lean on general knowledge by design, but is worth tightening in a v2 (e.g. retrieval from a structured substitution dataset rather than relying on the LLM's own knowledge).

---

## Deployment challenges

Worth documenting honestly, since this took longer than the ML work:

- **`scipy` build failure on Linux** — `pip freeze` from local macOS pinned a scipy version with no prebuilt Linux/Python 3.13 wheel, so the build tried compiling from source and failed on a missing Fortran compiler. Fixed with Python-version-conditional pins.
- **`libgomp.so.1` missing at runtime** — LightGBM's compiled binary needs the system-level OpenMP library, which isn't in Railway's default image. Fixed via an explicit Dockerfile installing `libgomp1`.
- **Docker `CMD` array form doesn't expand env vars** — `port $PORT` was passed as a literal string, not substituted, until switched to shell form.
- **1.3GB RAM spike on startup** — loading the recipe catalog via pandas caused an OOM kill on a 500MB container. Rewrote the hot path to SQLite (with FTS5 for search) instead of an in-memory DataFrame, cutting startup memory to ~284MB.
- **Supabase's IPv6-only direct connection** wasn't reachable from Railway's default egress — switched to Supabase's connection pooler (session mode, to avoid PgBouncer prepared-statement issues).
- **Vercel 404 despite a clean build** — in a monorepo without an explicit Next.js framework preset, Vercel defaulted to "Other" and looked for a static `dist/` folder instead of `.next/`. Fixed by setting the framework preset explicitly.

## Security

- Row-Level Security enabled on all public Postgres tables.
- Ownership verification on every user-scoped route (a JWT's user can only read/write their own data) — caught and fixed a real IDOR gap on the preferences endpoints during a dedicated security pass.
- Parameterized queries throughout (no raw SQL string interpolation).
- Rate limiting on LLM-backed endpoints to protect the (free-tier) Groq quota from abuse.
- Generic error responses in production (no stack traces or DB details leaked to clients).

**Known limitation:** Supabase's leaked-password protection (HaveIBeenPwned check) requires their paid tier and isn't enabled on this free-tier deployment — documented rather than silently skipped.

---

## Running locally

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

Requires `.env` files (see `.env.example` in each folder) for Supabase, Groq, and database credentials.

## What I'd do with more time

- Structured substitution data (rather than relying purely on LLM knowledge) to close the SUBS hallucination gap.
- A proper multi-turn retrieval evaluation harness, since the current REFINE/SUBS retrieval numbers are inconclusive rather than resolved.
- Full recipe catalog embeddings (currently scoped to the most-interacted-with subset for compute reasons during development).

---

*Built as an independent extension of a coursework project — same underlying skillset (recommender systems, embeddings, RAG), different dataset, different domain, and a real deployed product instead of a notebook dashboard.*
