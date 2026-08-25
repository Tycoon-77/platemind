import re

with open("backend/ml/13_eval_chat.py", "r") as f:
    text = f.read()

# Replace check_hallucination_llm
old_func = """def check_hallucination_llm(reply: str, recipes: list[dict]) -> bool:
    if not reply or not recipes: return True
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = ""
    for r in recipes:
        context += f"- {r.get('name')} (ID: {r.get('recipe_id')}): {r.get('minutes')} mins. Ingredients: {', '.join(r.get('ingredients', []))}. Tags: {', '.join(r.get('tags', []))}\\n"
    
    prompt = f\"\"\"
You are evaluating an AI assistant's reply for hallucinations. 
The assistant was provided with the following recipes as context:
{context}

The assistant generated this reply:
"{reply}"

Analyze every factual claim in the reply regarding recipes, ingredients, times, or tags. 
Are there any factual claims in the reply that are NOT supported by the context?
Answer exactly "YES" if there is a hallucination (unsupported claim), or "NO" if all claims are supported or it's a general safe statement. Only output YES or NO.
\"\"\"
    try:
        # Use a faster, lighter model for judgment to save TPM limits
        ans = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip().upper()
        return "YES" not in ans
    except Exception as e:
        print("Groq Judge error:", e)
        return True # Fallback"""

new_func = """def check_hallucination_llm(reply: str, recipes: list[dict], intent: str) -> bool:
    if not reply or not recipes: return True
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = ""
    for r in recipes:
        context += f"- {r.get('name')} (ID: {r.get('recipe_id')}): {r.get('minutes')} mins. Ingredients: {', '.join(r.get('ingredients', []))}. Tags: {', '.join(r.get('tags', []))}\\n"
    
    if intent == "SUBS":
        prompt = f\"\"\"
You are evaluating an AI assistant's reply for hallucinations on a substitution question. 
The assistant was provided with the following recipes as context:
{context}

The assistant generated this reply:
"{reply}"

The assistant is ALLOWED to use general world knowledge to suggest ingredient substitutions.
However, it must NOT invent facts about the retrieved recipes themselves.
Are there any factual claims in the reply ABOUT the specific retrieved recipes (e.g., claiming a recipe contains an ingredient it does not, or has a different cook time) that are NOT supported by the context?
Answer exactly "YES" if there is a recipe hallucination, or "NO" if the recipe facts are supported (or not mentioned) and the rest is just safe substitution advice. Only output YES or NO.
\"\"\"
    else:
        prompt = f\"\"\"
You are evaluating an AI assistant's reply for hallucinations on a recipe search. 
The assistant was provided with the following recipes as context:
{context}

The assistant generated this reply:
"{reply}"

Analyze every factual claim in the reply regarding recipes, ingredients, times, or tags. 
Are there any factual claims in the reply that are NOT supported by the context?
Answer exactly "YES" if there is a hallucination (unsupported claim), or "NO" if all claims are supported or it's a general safe statement. Only output YES or NO.
\"\"\"
    try:
        ans = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip().upper()
        return "YES" not in ans
    except Exception as e:
        print("Groq Judge error:", e)
        return True"""

text = text.replace(old_func, new_func)

# Fix check_hallucination_llm call
text = text.replace(
    "hallucination_free = check_hallucination_llm(reply, recs)",
    "hallucination_free = check_hallucination_llm(reply, recs, expected_intent)"
)

text = text.replace(
    "actual_intent = actual_intent",
    "expected_intent = expected_intent"
)

# Replace the reporting block
old_report_block = """total = len(results)
rel_ok  = sum(1 for r in results if r["retrieval_ok"])
hall_ok = sum(1 for r in results if r["hallucination_free"])
sane_ok = sum(1 for r in results if r["reply_sane"])

report = f\"\"\"
## Phase 3 Strict LLM Eval Results (llama-3.1-8b-instant judge)
- **Retrieval Relevance**: {rel_ok}/{total} ({100*rel_ok//total}%)
- **Hallucination-free**:  {hall_ok}/{total} ({100*hall_ok//total}%)
- **Reply Sanity**:        {sane_ok}/{total} ({100*sane_ok//total}%)
\"\"\"

with open(Path(__file__).resolve().parents[1] / "eval_report.md", "a") as f:
    f.write("\\n" + report + "\\n")
print("\\nDone. Appended to eval_report.md")"""

new_report_block = """total = len(results)
rel_ok  = sum(1 for r in results if r["retrieval_ok"])
hall_ok = sum(1 for r in results if r["hallucination_free"])
sane_ok = sum(1 for r in results if r["reply_sane"])

gen_results = [r for r in results if r["expected_intent"] == "GENERAL"]
ref_results = [r for r in results if r["expected_intent"] == "REFINE"]
subs_results = [r for r in results if r["expected_intent"] == "SUBS"]

def _pct(num, den):
    return f"{num}/{den} ({int(100*num/den)}%)" if den > 0 else "N/A"

report = f\"\"\"
## Phase 3 Strict LLM Eval Results (openai/gpt-oss-20b judge, intent-aware)

**Overall**
- **Retrieval Relevance**: {_pct(rel_ok, total)}
- **Hallucination-free**:  {_pct(hall_ok, total)}
- **Reply Sanity**:        {_pct(sane_ok, total)}

**By Intent**
- GENERAL (10 queries):
  - Retrieval: {_pct(sum(1 for r in gen_results if r["retrieval_ok"]), len(gen_results))}
  - Hallucination-free: {_pct(sum(1 for r in gen_results if r["hallucination_free"]), len(gen_results))}
- REFINE (8 queries):
  - Retrieval: {_pct(sum(1 for r in ref_results if r["retrieval_ok"]), len(ref_results))}
  - Hallucination-free: {_pct(sum(1 for r in ref_results if r["hallucination_free"]), len(ref_results))}
- SUBS (7 queries):
  - Retrieval: {_pct(sum(1 for r in subs_results if r["retrieval_ok"]), len(subs_results))}
  - Hallucination-free: {_pct(sum(1 for r in subs_results if r["hallucination_free"]), len(subs_results))}
\"\"\"

with open(Path(__file__).resolve().parent / "eval_report.md", "a") as f:
    f.write("\\n" + report + "\\n")
print("\\nDone. Appended to eval_report.md")"""

text = text.replace(old_report_block, new_report_block)

# Also fix the expected_intent in the results dict
text = text.replace(
    '        "actual_intent": actual_intent,',
    '        "actual_intent": actual_intent,\n        "expected_intent": expected_intent,'
)

with open("backend/ml/13_eval_chat.py", "w") as f:
    f.write(text)
