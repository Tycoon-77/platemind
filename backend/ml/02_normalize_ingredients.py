"""
02_normalize_ingredients.py — Reusable ingredient normalization for PlateMind.

This module is imported by Phase 2's pantry-matching scorer and Phase 4's
/pantry API endpoint.  Keep the public API simple: normalize(text) → str.

Normalization pipeline (applied in order):
    1. Lowercase + strip leading/trailing whitespace.
    2. Remove quantity markers that slip through ("2 tbsp", "1/2 cup", etc.).
    3. Strip common preparation/state descriptors:
         chopped, diced, minced, sliced, shredded, grated, crushed, ground,
         fresh, frozen, canned, dried, cooked, raw, pitted, peeled, halved,
         quartered, thinly, finely, roughly, lightly, well, thoroughly, etc.
    4. Strip packaging/form words that shouldn't separate two pantry items:
         boneless, skinless, large, small, medium, extra, lean, whole, etc.
    5. Singularize using inflect (tomatoes → tomato, etc.).
    6. Strip & and + connectors when trailing ("salt & pepper" → "salt").
    7. Remove stray punctuation and collapse whitespace.

Design decisions documented:
    - "cherry tomatoes" → "cherry tomato" (NOT just "tomato").
      Qualifier adjectives that are meaningfully different ("cherry", "roma",
      "sun-dried") are preserved.  Only pure process words are stripped.
    - "all-purpose flour" → "all-purpose flour" (hyphenated qualifiers kept).
    - "salt and pepper" → "salt" (we take the first noun phrase before
      conjunctions).  This is a known approximation; Phase 2 can refine.

Run standalone to process the full cleaned recipes file:
    python backend/ml/02_normalize_ingredients.py

Outputs:
    data/processed/ingredients_normalized.parquet
       Columns: raw_name, normalized_name
       (all unique ingredient strings found across the dataset)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

import inflect
import pandas as pd
from tqdm import tqdm

# ── inflect engine (module-level singleton — thread-safe for reads) ───────────
_engine = inflect.engine()


# ─────────────────────────────────────────────────────────────────────────────
# Regex patterns (compiled once)
# ─────────────────────────────────────────────────────────────────────────────

# Quantity patterns: "2", "1/2", "½", "2-3"
_RE_QUANTITY = re.compile(
    r"^\d[\d/\-\.]*\s*"
    r"(?:cups?|tbsps?|tablespoons?|tsps?|teaspoons?|oz|ounces?|"
    r"lbs?|pounds?|grams?|g\b|kg\b|ml\b|liters?|litres?|"
    r"cans?|jars?|packages?|pkgs?|bags?|heads?|bunches?|"
    r"cloves?|stalks?|sprigs?|slices?|pieces?|pinch(?:es)?|dash(?:es)?)?\s*",
    re.IGNORECASE,
)

# Preparation descriptors to remove (as whole words)
_PREP_DESCRIPTORS = {
    # State
    "fresh", "freshly", "frozen", "canned", "dried", "dry", "cooked",
    "raw", "uncooked", "prepared", "ready", "instant",
    # Cut / process
    "chopped", "diced", "minced", "sliced", "shredded", "grated",
    "crushed", "ground", "mashed", "pureed", "crumbled", "crumble",
    "pitted", "peeled", "halved", "quartered", "cubed", "julienned",
    "zested", "squeezed", "pressed", "packed",
    # Adverbs modifying prep
    "thinly", "finely", "roughly", "coarsely", "lightly", "well",
    "thoroughly", "heavily", "loosely", "firmly", "gently",
    # Size qualifiers that don't change identity
    "large", "medium", "small", "tiny", "thick", "thin", "bite-sized",
    # Quality / source
    "organic", "natural", "low-fat", "nonfat", "fat-free", "reduced-fat",
    "low-sodium", "unsalted", "salted", "roasted", "toasted", "smoked",
    "extra-virgin", "extra virgin", "pure", "plain", "original",
    # Packaging
    "boneless", "skinless", "bone-in", "skin-on",
    # Timing
    "overnight", "quick",
}

_RE_PREP = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _PREP_DESCRIPTORS) + r")\b",
    re.IGNORECASE,
)

# Conjunction split: take the part BEFORE "and", "&", "or", "+"
# e.g. "salt and pepper" → "salt"
_RE_CONJUNCTION = re.compile(r"\s+(?:and|or|&|\+)\s+.*$", re.IGNORECASE)

# Stray punctuation (keep hyphens inside words like "all-purpose")
_RE_STRAY_PUNCT = re.compile(r"[,;:\(\)\[\]\{\}\"\'!?@#\$%\^*=<>]")

# Collapse multiple whitespace
_RE_WHITESPACE = re.compile(r"\s{2,}")


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Normalize a raw ingredient string to a canonical form suitable for
    pantry matching and ingredient deduplication.

    Parameters
    ----------
    text : str
        Raw ingredient string from the Food.com dataset or user input.

    Returns
    -------
    str
        Normalized ingredient string, or empty string if input is nonsensical.

    Examples
    --------
    >>> normalize("2 cups freshly chopped Tomatoes")
    'tomato'
    >>> normalize("extra-virgin olive oil")
    'olive oil'
    >>> normalize("boneless skinless chicken breasts")
    'chicken breast'
    >>> normalize("salt and pepper")
    'salt'
    >>> normalize("all-purpose flour")
    'all-purpose flour'
    >>> normalize("cherry tomatoes")
    'cherry tomato'
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    s = text.strip()

    # 1. Lowercase
    s = s.lower()

    # 2. Remove leading quantity + unit
    s = _RE_QUANTITY.sub("", s).strip()

    # 3. Strip prep/state descriptors
    s = _RE_PREP.sub(" ", s).strip()

    # 4. Conjunction split — take first noun phrase
    s = _RE_CONJUNCTION.sub("", s).strip()

    # 5. Strip stray punctuation
    s = _RE_STRAY_PUNCT.sub(" ", s)

    # 6. Collapse whitespace
    s = _RE_WHITESPACE.sub(" ", s).strip()

    if not s:
        return ""

    # 7. Singularize the LAST word only (handles "chicken breasts" → "chicken breast",
    #    "cherry tomatoes" → "cherry tomato", etc.)
    parts = s.split()
    last = parts[-1]
    singular = _engine.singular_noun(last)
    if singular and isinstance(singular, str):
        parts[-1] = singular
    s = " ".join(parts)

    # 8. Final strip
    s = s.strip(" -")

    return s


def normalize_many(texts: List[str]) -> List[str]:
    """Vectorized normalize over a list of ingredient strings."""
    return [normalize(t) for t in texts]


# ─────────────────────────────────────────────────────────────────────────────
# Standalone: build a full normalized ingredient lookup table
# ─────────────────────────────────────────────────────────────────────────────

def build_ingredient_table(recipes_parquet: Path) -> pd.DataFrame:
    """
    Extract all unique raw ingredient strings from the cleaned recipes,
    normalize each, and return a DataFrame with columns:
        raw_name, normalized_name

    This table is the canonical ingredient vocabulary for the app.
    """
    r = pd.read_parquet(recipes_parquet)

    # Flatten all ingredient lists into a single series
    all_raw = pd.Series(
        [ing for ing_list in r["ingredients"] for ing in ing_list],
        name="raw_name",
    )
    unique_raw = all_raw.drop_duplicates().reset_index(drop=True)

    print(f"  Unique raw ingredient strings: {len(unique_raw):,}")

    tqdm.pandas(desc="  Normalizing")
    normalized = unique_raw.progress_apply(normalize)

    df = pd.DataFrame({"raw_name": unique_raw, "normalized_name": normalized})

    # Flag empty normalizations (should be rare — mostly junk entries)
    empty = (df["normalized_name"] == "").sum()
    print(f"  Empty after normalization: {empty} (will be kept as-is with raw name)")
    df.loc[df["normalized_name"] == "", "normalized_name"] = df.loc[
        df["normalized_name"] == "", "raw_name"
    ]

    return df


if __name__ == "__main__":
    ROOT = Path(__file__).resolve().parent.parent
    PROCESSED = ROOT / "data" / "processed"
    PROCESSED.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PHASE 1 — Step 2: Ingredient Normalization")
    print("=" * 60)

    # Quick sanity-check examples
    print("\n--- Normalization examples ---")
    examples = [
        "2 cups freshly chopped Tomatoes",
        "extra-virgin olive oil",
        "boneless skinless chicken breasts",
        "salt and pepper",
        "all-purpose flour",
        "cherry tomatoes",
        "1/2 cup finely diced onions",
        "canned diced tomatoes",
        "fresh garlic cloves",
        "low-fat sour cream",
        "frozen chopped broccoli",
        "ground beef",
        "unsalted butter",
        "large eggs",
        "grated parmesan cheese",
    ]
    for ex in examples:
        print(f"  {ex!r:<45} → {normalize(ex)!r}")

    # Build full ingredient table
    print("\n[1/2] Building normalized ingredient lookup table…")
    recipes_parquet = PROCESSED / "recipes_clean.parquet"
    if not recipes_parquet.exists():
        print("ERROR: Run 01_explore.py first to generate recipes_clean.parquet")
        sys.exit(1)

    ing_df = build_ingredient_table(recipes_parquet)

    out_path = PROCESSED / "ingredients_normalized.parquet"
    ing_df.to_parquet(out_path, index=False)
    print(f"\n[2/2] Saved → data/processed/ingredients_normalized.parquet ({len(ing_df):,} rows)")

    # Show top normalized ingredients by frequency
    r = pd.read_parquet(recipes_parquet)
    flat = pd.Series([normalize(ing) for ing_list in r["ingredients"] for ing in ing_list])
    print("\nTop 20 normalized ingredients by frequency:")
    print(flat.value_counts().head(20).to_string())

    print("\n✅  02_normalize_ingredients.py complete.")
