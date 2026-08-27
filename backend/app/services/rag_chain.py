"""
rag_chain.py — LangChain RAG retrieval chain over pgvector + Groq LLM.

Public API:
    build_chain(session_id, history)  → (chain, retriever)
    invoke_rag(message, session_id, history)
      → {"reply", "retrieved_recipe_ids", "updated_results"}

Design decisions:
  - Retriever: pgvector cosine similarity via langchain-postgres
    PGVector store, returning top-8 docs.
  - LLM: Groq llama-3.3-70b-versatile (fast, free-tier).
  - Three prompt branches (classified by a cheap keyword heuristic before the
    LLM call):
      REFINE   — "make it vegetarian / under 20 minutes / less spicy"
      SUBS     — "substitute X / I don't have Y"
      GENERAL  — everything else (open recipe questions)
  - Rate-limit guardrail: in-memory TTL cache keyed on (session_id, message).
    Identical query within 60 s returns cached response without hitting Groq.
    If Groq returns 429/503, a clean fallback string is returned.
"""

import os, time, hashlib
from typing import List, Optional
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ---------------------------------------------------------------------------
# TTL cache (in-memory, per process)
# ---------------------------------------------------------------------------
_CACHE: dict[str, tuple[float, dict]] = {}   # key -> (timestamp, result)
_CACHE_TTL = 60.0  # seconds


def _cache_key(session_id: str, message: str) -> str:
    return hashlib.sha256(f"{session_id}::{message}".encode()).hexdigest()[:24]


def _from_cache(session_id: str, message: str) -> Optional[dict]:
    key = _cache_key(session_id, message)
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _CACHE[key]
    return None


def _to_cache(session_id: str, message: str, result: dict):
    key = _cache_key(session_id, message)
    _CACHE[key] = (time.time(), result)


# ---------------------------------------------------------------------------
# Intent classification (cheap keyword heuristic — no LLM call)
# ---------------------------------------------------------------------------
_REFINE_KEYWORDS = {
    "vegetarian", "vegan", "gluten", "dairy", "nut", "minutes", "quick",
    "under", "faster", "less", "simpler", "easy", "healthier", "low calorie",
    "low carb", "keto", "paleo",
}
_SUBS_KEYWORDS = {
    "substitute", "replace", "instead of", "without", "alternative",
    "don't have", "dont have", "out of", "swap",
}


def _classify_intent(message: str) -> str:
    m = message.lower()
    if any(k in m for k in _SUBS_KEYWORDS):
        return "SUBS"
    if any(k in m for k in _REFINE_KEYWORDS):
        return "REFINE"
    return "GENERAL"


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_STRICT = """You are PlateMind, a friendly, conversational, and highly readable culinary AI assistant.
You help users find recipes that match their pantry, dietary needs, and taste preferences.

GROUNDING RULES — follow these strictly:
- Only state facts that literally appear in the retrieved recipe context provided below.
- Do NOT infer, estimate, or embellish any detail (e.g. calories, exact quantities, steps) that is absent from the context.
- NEVER list the raw internal tags (like 'time-to-make', 'course', 'main-ingredient'). They are ugly database artifacts.
- If the user asks about something not covered by the retrieved context, respond with "I don't have that information in the current recipe results" rather than guessing.
- Format your response naturally in a conversational, human-friendly way (e.g. using bullet points, bolding recipe names). Do not just regurgitate raw database text.

Be concise, warm, and highly readable."""

_PROMPT_REFINE = """{system_strict}

The user wants to refine the current recipe results:
User said: "{message}"

Retrieved recipes from the database:
{context}

Based on these recipes and the user's refinement request, suggest the best matching
options and explain which dietary/time constraints they satisfy. Include recipe names."""

_SYSTEM_SUBS = _SYSTEM_STRICT

_PROMPT_SUBS = """{system_subs}

The user has a substitution or "what if I don't have X" question:
User said: "{message}"

Retrieved recipes from the database:
{context}

Provide practical substitution advice grounded in your culinary knowledge. If a retrieved
recipe relies heavily on the missing ingredient, warn them. Do not hallucinate details
about the recipes themselves."""

_PROMPT_GENERAL = """{system_strict}

The user has a general recipe question:
User said: "{message}"

Retrieved recipes from the database:
{context}

If the user is just saying hi or greeting you, greet them warmly and ask how you can help them find a recipe (ignore the context). Otherwise, answer the user's question using ONLY the provided recipe context. Recommend options
that best fit their query. Include recipe names."""

_TEMPLATES = {
    "REFINE":  _PROMPT_REFINE,
    "SUBS":    _PROMPT_SUBS,
    "GENERAL": _PROMPT_GENERAL,
}

_embeddings_model = None

def _get_embeddings():
    global _embeddings_model
    if _embeddings_model is None:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        _embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings_model


def _retrieve_recipes(query: str, top_k: int = 8) -> list[dict]:
    """
    Embed `query` then hit pgvector for nearest recipes.
    Returns list of recipe dicts with keys: recipe_id, name, minutes,
    tags, ingredients.
    """
    from sqlalchemy import create_engine, text as sql_text
    import numpy as np

    emb_model = _get_embeddings()
    query_vec = emb_model.embed_query(query)
    vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    with eng.connect() as conn:
        rows = conn.execute(sql_text("""
            SELECT recipe_id, name, minutes, tags, ingredients,
                   1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM recipes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """), {"vec": vec_str, "k": top_k}).fetchall()

    results = []
    for r in rows:
        results.append({
            "recipe_id":   r.recipe_id,
            "name":        r.name,
            "minutes":     r.minutes,
            "tags":        list(r.tags or []),
            "ingredients": list(r.ingredients or []),
            "similarity":  round(float(r.similarity), 4),
        })
    return results


# ---------------------------------------------------------------------------
# Contextual query rewriting (REFINE / SUBS only)
# ---------------------------------------------------------------------------
_REWRITE_MODEL = "openai/gpt-oss-120b"   # cheap, fast — never the 120B


def _rewrite_query(message: str, history: list[dict]) -> str:
    """
    Fuse the current REFINE/SUBS message with the most recent user turn from
    history into a self-contained retrieval query.

    Example:
      history[-2] = {"role": "user",      "content": "Show me a quick chicken dinner"}
      message     = "Make it vegetarian"
      → "vegetarian quick chicken dinner"

    Falls back to the original message on any error.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "placeholder-groq-key":
        return message

    # Extract the last user turn (skip the latest assistant reply)
    prior_user = ""
    for turn in reversed(history):
        if turn.get("role") == "user":
            prior_user = turn["content"]
            break

    if not prior_user:
        return message   # no prior context — nothing to fuse

    prompt = (
        "You are a search query optimizer for a recipe search engine.\n"
        "Given a PRIOR user request and a FOLLOW-UP message, produce a single "
        "self-contained recipe search query (8 words max, no punctuation) that "
        "captures both the original topic and the follow-up constraint.\n"
        "Output ONLY the search query — no explanation, no quotes.\n\n"
        f"PRIOR: {prior_user}\n"
        f"FOLLOW-UP: {message}\n"
        "SEARCH QUERY:"
    )

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=_REWRITE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=24,
            temperature=0.0,
        )
        rewritten = resp.choices[0].message.content.strip().strip('"').strip("'")
        print(f"[rag_chain] query rewrite: '{message}' + prior → '{rewritten}'")
        return rewritten if rewritten else message
    except Exception as exc:
        print(f"[rag_chain] rewrite error ({type(exc).__name__}): {exc}")
        return message


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def invoke_rag(
    message: str,
    session_id: str,
    history: Optional[List[dict]] = None,
) -> dict:
    """
    Full RAG pipeline:
      1. TTL cache check.
      2. Classify intent (needed before retrieval for query rewriting).
      3. Rewrite query for REFINE/SUBS using prior history turn (cheap LLM call).
      4. Retrieve relevant recipes from pgvector using the (possibly rewritten) query.
      5. Build prompt + call main Groq LLM.
      6. Return {reply, retrieved_recipe_ids, updated_results}.

    On Groq rate-limit (429) → clean fallback string, no 500.
    """
    history = history or []

    # 1. Cache check
    cached = _from_cache(session_id, message)
    if cached:
        cached["from_cache"] = True
        return cached

    # 2. Classify intent first — needed to decide whether to rewrite
    intent = _classify_intent(message)

    # 3. Contextual query rewriting for REFINE / SUBS
    #    Fuse the follow-up message with the prior user turn so the pgvector
    #    retriever gets a self-contained query instead of a pronoun-heavy fragment.
    retrieval_query = message
    if intent in ("REFINE", "SUBS") and history:
        retrieval_query = _rewrite_query(message, history)

    # 4. Retrieve using the (possibly rewritten) query
    try:
        retrieved = _retrieve_recipes(retrieval_query, top_k=8)
    except Exception as e:
        retrieved = []
        print(f"[rag_chain] retrieval error: {e}")

    recipe_ids = [r["recipe_id"] for r in retrieved]

    # 5. Format context block
    context_lines = []
    for r in retrieved:
        ings = ", ".join(r["ingredients"][:8])
        tags = ", ".join(r["tags"][:5])
        context_lines.append(
            f"- **{r['name']}** ({r['minutes']} min) | ingredients: {ings}"
        )
    context_str = "\n".join(context_lines) if context_lines else "No recipes retrieved."

    # Build prompt using the original user message (not the rewritten query)
    template = _TEMPLATES[intent]
    prompt_text = template.format(
        system_strict=_SYSTEM_STRICT,
        system_subs=_SYSTEM_SUBS,
        message=message,
        context=context_str,
    )

    # 5. Groq LLM call
    reply = ""
    if not GROQ_API_KEY or GROQ_API_KEY == "placeholder-groq-key":
        reply = (
            "[Demo mode — no Groq API key set]\n\n"
            f"I found {len(retrieved)} relevant recipes for you:\n"
            + "\n".join(f"• {r['name']} ({r['minutes']} min)" for r in retrieved[:5])
        )
    else:
        try:
            from groq import Groq, RateLimitError
            client = Groq(api_key=GROQ_API_KEY)

            # Include last 4 history turns for context
            messages = []
            for turn in history[-4:]:
                messages.append({"role": turn["role"], "content": turn["content"]})
            messages.append({"role": "user", "content": prompt_text})

            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=1536,
                temperature=0.4,
            )
            reply = resp.choices[0].message.content.strip()

        except Exception as exc:
            exc_name = type(exc).__name__
            if "RateLimit" in exc_name or "429" in str(exc):
                reply = (
                    "I'm getting a lot of requests right now — please try again in a moment! "
                    "In the meantime, here are some recipes that match your query:\n\n"
                    + "\n".join(f"• {r['name']} ({r['minutes']} min)" for r in retrieved[:5])
                )
            else:
                reply = (
                    "Something went wrong with the AI assistant. "
                    "Here are some recipes that might help:\n\n"
                    + "\n".join(f"• {r['name']} ({r['minutes']} min)" for r in retrieved[:5])
                )
            print(f"[rag_chain] Groq error ({exc_name}): {exc}")

    result = {
        "reply":                reply,
        "intent":               intent,
        "retrieved_recipe_ids": recipe_ids,
        "updated_results":      retrieved,
        "from_cache":           False,
    }

    _to_cache(session_id, message, result)
    return result
