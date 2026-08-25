# PlateMind — Phase 1 Baseline Evaluation Report

## Setup

| Parameter | Value |
|---|---|
| Dataset | Food.com Recipes & Interactions (Kaggle) |
| Split | Leave-last-out (chronological per user) |
| Warm threshold | ≥ 3 interactions per user AND per recipe |
| Train interactions | 699,670 |
| Test interactions | 35,336 |
| Evaluation users | ≤ 5,000 (sampled if larger) |
| Catalog size | 89,405 unique recipes |
| Metric K | 10 |

## Results

| Model | Precision@10 | Recall@10 | Coverage | Users Evaluated |
|---|---|---|---|---|
| Popularity | 0.0006 | 0.0060 | 0.0002 | 500 |
| UserCF | 0.0017 | 0.0166 | 0.0280 | 483 |
| ItemCF | 0.0014 | 0.0145 | 0.0392 | 483 |
| MatrixFactorization (ALS) ⭐ | 0.0021 | 0.0207 | 0.0111 | 483 |

⭐ = best on Precision@10

## Interpretation

### Precision@10
Fraction of the top-10 recommendations that match the held-out item.
Since each user has exactly **one** held-out item, the theoretical ceiling
for Precision@10 is 1/10 = 0.1000 (if the model perfectly places the
held-out item in any of the top-10 slots).  Real values are well below this
because the recommendation space is large (89,405 items).

### Recall@10
Identical to Precision@10 in the leave-one-out setup (single relevant item),
so these columns should match.  Slight differences arise from skipped users.

### Coverage
Fraction of the catalog that appears in at least one recommendation across all
evaluated users.  **High coverage = diverse recommendations** (less "filter
bubble").  Popularity naturally has low coverage; CF models tend to be higher.

## Key Findings

1. **Popularity baseline** provides a reasonable floor and high coverage
   because the same popular items are recommended to everyone.

2. **User-Based CF** improves personalization but scales quadratically with
   user count — the similarity matrix is O(n_users²).  At this scale it is
   still tractable, but Phase 2 replaces it with the hybrid LightGBM ranker.

3. **Item-Based CF** tends to perform comparably to User-CF and is more stable
   as the item set is smaller than the user set here.

4. **Matrix Factorization (ALS)** via `implicit` treats ratings as confidence
   weights (1 + α * rating) and learns dense latent factors.  It typically
   offers the best precision among the four baselines.

## What Phase 2 Adds

- **Pantry-match scoring** (ingredient overlap, TF-IDF weighted by rarity).
- **Recipe content embeddings** (sentence-transformers → pgvector).
- **Dietary hard-filters** applied *before* ranking (allergies are a constraint,
  not a signal).
- **LightGBM hybrid ranker** blending all signals; tuned with Optuna.
- Target: ≥ 2× improvement in NDCG@10 over the best baseline here.

## Limitations

- **Rating sparsity**: most users have very few interactions; cold-start
  users (< 3 interactions) are excluded entirely and need the popularity
  fallback or pantry-match-only path.
- **Implicit negative signals**: rating == 0 rows (user reviewed without
  rating) are excluded from CF training.  Phase 2 will use them as
  implicit positive signals (viewed/engaged = mild preference).
- **Temporal drift**: the dataset spans 2000–2018; user tastes likely
  evolved.  A time-decayed weighting scheme could improve recency.


## Phase 2: Hybrid Ranker Evaluation

| Model | NDCG@10 |
|---|---|
| MatrixFactorization (ALS) | 0.3454 |
| LightGBM Hybrid | 0.4852 |

*Evaluated on a simulated test set of 100 users, ranking 20 candidate recipes per user using CF score, Embedding Similarity, and Pantry Match Score.*
## Leakage Check Findings
A data leakage check was performed to verify the integrity of the evaluation:
1. **Train/Test Split**: Confirmed to be strictly chronological (leave-last-interaction-out per user). No future interactions are used during training.
2. **Pantry Overlap**: A check was run to see if the held-out test recipe's ingredients appeared in the user's simulated pantry (which was built strictly from *past* interacted recipes).
   - **Finding**: 438 out of 500 users (87.6%) had overlapping ingredients between their past recipes and their held-out test recipe.
   - **Conclusion**: This is **not a data leak**, but rather a validation of the core hypothesis: users exhibit highly consistent ingredient preferences over time (e.g., repeatedly using staples like olive oil, garlic, or chicken). This consistency is exactly what the `PantryMatcher` exploits to improve ranking.


## Phase 3: RAG /chat Eval (25 queries)

| Query | Expected | Actual | Retrieval | Hall-free | Sane |
|-------|----------|--------|-----------|-----------|------|
| Show me a quick chicken dinner for weeknights           | GENERAL | REFINE  | ✅ | ✅ | ✅ |
| I want something with salmon and lemon                  | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| What can I make with pasta and tomatoes?                | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| Give me a hearty beef stew recipe                       | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| Something with shrimp and garlic                        | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| I want a breakfast egg dish                             | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| Find me a soup with vegetables                          | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| What is a good chocolate dessert?                       | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| Show me Indian spiced dishes                            | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| I want a salad with avocado                             | GENERAL | GENERAL | ✅ | ✅ | ✅ |
| Make it vegetarian                                      | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| Only show me recipes under 20 minutes                   | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| I need something gluten free                            | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| Something simpler and less spicy please                 | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| Lower calorie version please                            | REFINE  | GENERAL | ✅ | ✅ | ✅ |
| Can you make it vegan?                                  | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| I need a dairy free option                              | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| Make it a quicker recipe — under 30 minutes             | REFINE  | REFINE  | ✅ | ✅ | ✅ |
| Can I substitute butter with olive oil?                 | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| What if I don't have heavy cream?                       | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| I don't have garlic — what can I use instead?           | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| Replace chicken with tofu in the recipe                 | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| What can I use instead of soy sauce?                    | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| I'm out of eggs — how do I substitute them?             | SUBS    | SUBS    | ✅ | ✅ | ✅ |
| Can I swap flour for almond flour in baking?            | SUBS    | SUBS    | ✅ | ✅ | ✅ |

**Summary**

| Metric | Score |
|--------|-------|
| Overall pass | 25/25 (100%) |
| Retrieval relevance | 25/25 (100%) |
| Hallucination-free | 25/25 (100%) |
| Reply sanity | 25/25 (100%) |
| Intent classification accuracy | 23/25 (92%) |

*Intent classifier uses keyword heuristics (no LLM call).*
*Hallucination check: quoted recipe names in reply must appear in retrieved set.*

## Phase 3 Strict LLM Eval Methodology Update
**Retrieval Relevance**: Replaced substring check with strict hit/miss against manually-labeled expected recipe IDs (ground truth). This checks if the pgvector search actually surfaces the exact best recipes for a query.
**Hallucination Check**: Replaced naive quote matching with an LLM-as-a-judge (Groq). Every factual claim (ingredients, time, tags) in the generated reply is checked against the retrieved context to ensure the model isn't fabricating details.
**Reply Sanity**: Checks if the response is non-empty and >20 chars (smoke test).



## Phase 3 Strict LLM Eval Results (openai/gpt-oss-20b judge)
- **Retrieval Relevance**: 10/25 (40%)
- **Hallucination-free**:  14/25 (56%)
- **Reply Sanity**:        25/25 (100%)

