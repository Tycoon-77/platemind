from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, recipes, recommend, chat, pantry, favorites, mealplan

from contextlib import asynccontextmanager
from app.ml_state import init_ml_state

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_ml_state()
    yield
    # Shutdown

app = FastAPI(
    title="PlateMind API",
    description="AI-powered pantry-first recipe recommender & conversational meal planner",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server during development.
# Tighten origins list for production.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        # Add Vercel URL here once deployed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(recipes.router, prefix="/recipes", tags=["recipes"])
app.include_router(recommend.router, prefix="/recommend", tags=["recommend"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(pantry.router, prefix="/pantry", tags=["pantry"])
app.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
app.include_router(mealplan.router, prefix="/mealplan", tags=["mealplan"])


@app.get("/health", tags=["meta"])
async def health_check():
    """Liveness probe — used by uptime monitors to keep the service warm."""
    return {"status": "ok", "service": "platemind-api"}
