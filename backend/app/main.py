from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, recipes, recommend, chat, pantry, favorites, mealplan


from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
import os

from app.limiter import limiter

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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# Global Exception Handler for Production (no stack traces)
# ---------------------------------------------------------------------------
from fastapi.responses import JSONResponse
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Let standard HTTP exceptions (like 401, 404, RateLimitExceeded) pass through
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    # Hide traceback for generic 500 exceptions
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )


# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server during development.
# Tighten origins list for production.
# ---------------------------------------------------------------------------
# Parse CORS_ORIGINS as a comma-separated list
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
