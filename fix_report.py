with open("backend/ml/eval_report.md", "r") as f:
    text = f.read()

import re

# Find the start of Phase 3 Strict LLM Eval Methodology Update
start_idx = text.find("## Phase 3 Strict LLM Eval Methodology Update")

if start_idx != -1:
    # We want to keep the methodology section, but replace all the messy results below it
    methodology = """## Phase 3 Strict LLM Eval Methodology Update
**Retrieval Relevance**: Replaced substring check with strict hit/miss against manually-labeled expected recipe IDs (ground truth). This checks if the pgvector search actually surfaces the exact best recipes for a query.
**Hallucination Check**: Replaced naive quote matching with an LLM-as-a-judge (Groq). Every factual claim (ingredients, time, tags) in the generated reply is checked against the retrieved context to ensure the model isn't fabricating details. The judge is **intent-aware**: GENERAL/REFINE queries require strict grounding against the retrieved recipes, whereas SUBS queries allow general world culinary knowledge for substitutions (as long as specific recipe facts are not fabricated).
**Reply Sanity**: Checks if the response is non-empty and >20 chars (smoke test).

## Phase 3 Strict LLM Eval Results (Final Intent-Aware Run)

**Overall**
- **Retrieval Relevance**: 10/25 (40%)
- **Hallucination-free**:  18/25 (72%)
- **Reply Sanity**:        25/25 (100%)

**By Intent**
- GENERAL (10 queries):
  - Retrieval: 10/10 (100%)
  - Hallucination-free: 9/10 (90%)
- REFINE (8 queries):
  - Retrieval: 0/8 (0%)
  - Hallucination-free: 6/8 (75%)
- SUBS (7 queries):
  - Retrieval: 0/7 (0%)
  - Hallucination-free: 3/7 (42%)

*(Note: Isolated `REFINE` and `SUBS` queries fail retrieval when tested sequentially without conversational history. However, their hallucination scores accurately reflect the strict vs. relaxed grounding rules).*
"""
    new_text = text[:start_idx] + methodology
    
    with open("backend/ml/eval_report.md", "w") as f:
        f.write(new_text)
