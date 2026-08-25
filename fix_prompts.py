import re

with open("backend/app/services/rag_chain.py", "r") as f:
    text = f.read()

# Let's replace the whole section from # Prompt templates down to the _TEMPLATES dict
new_section = '''# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_SYSTEM_STRICT = """You are PlateMind, a friendly and knowledgeable culinary AI assistant.
You help users find recipes that match their pantry, dietary needs, and taste preferences.

GROUNDING RULES — follow these strictly:
- Only state ingredients, cook times, tags, or any other facts that literally appear in the retrieved recipe context provided below.
- Do NOT infer, estimate, or embellish any detail (e.g. calories, exact quantities, steps) that is absent from the context.
- If the user asks about something not covered by the retrieved context, respond with "I don't have that information in the current recipe results" rather than guessing.
- When referencing a recipe, use only its name, cook time, tags, and ingredients as listed in the context — nothing more.

Be concise (3-5 sentences max)."""

_SYSTEM_SUBS = """You are PlateMind, a friendly and knowledgeable culinary AI assistant.

GROUNDING RULES:
- You may use your general culinary world knowledge to suggest ingredient substitutions.
- However, when referencing the specific retrieved recipes in the context, you must NOT fabricate or infer specifics (like their exact ingredients, cook times, or tags) that are not provided. Use the context strictly for recipe facts.
- Do not invent steps or quantities for the retrieved recipes.

Be concise (3-5 sentences max)."""

_PROMPT_REFINE = """{system_strict}

The user wants to refine the current recipe results:
User said: "{message}"

Retrieved recipes from the database:
{context}

Based on these recipes and the user's refinement request, suggest the best matching
options and explain which dietary/time constraints they satisfy. Include recipe names."""

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

Answer the user's question using ONLY the provided recipe context. Recommend options
that best fit their query. Include recipe names."""

_TEMPLATES = {
    "REFINE":  _PROMPT_REFINE,
    "SUBS":    _PROMPT_SUBS,
    "GENERAL": _PROMPT_GENERAL,
}'''

start_marker = "# ---------------------------------------------------------------------------\n# Prompt templates\n# ---------------------------------------------------------------------------"
end_marker = "def _get_embeddings():"

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

new_text = text[:start_idx] + new_section + "\n\n" + text[end_idx:]

with open("backend/app/services/rag_chain.py", "w") as f:
    f.write(new_text)

