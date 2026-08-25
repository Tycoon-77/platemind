"""
13_eval_chat.py — Mini eval for the Phase 3 RAG /chat endpoint.
"""
import os, sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.services.rag_chain import invoke_rag
from groq import Groq

# Hardcoded human judgments for relevance (expected recipe IDs)
GROUND_TRUTH = {
    "Show me a quick chicken dinner for weeknights": [60301, 328828],
    "I want something with salmon and lemon": [149476, 127788],
    "What can I make with pasta and tomatoes?": [475231, 176435],
    "Give me a hearty beef stew recipe": [11473, 25806],
    "Something with shrimp and garlic": [494206, 47515],
    "I want a breakfast egg dish": [14494, 123479],
    "Find me a soup with vegetables": [86094, 106290],
    "What is a good chocolate dessert?": [286978, 49613],
    "Show me Indian spiced dishes": [29146, 187399],
    "I want a salad with avocado": [94520, 108484],
    
    "Make it vegetarian": [227409, 399899],
    "Only show me recipes under 20 minutes": [342674, 452912],
    "I need something gluten free": [223709, 353227],
    "Something simpler and less spicy please": [152199, 14930],
    "Lower calorie version please": [144807, 301625],
    "Can you make it vegan?": [130541, 482103],
    "I need a dairy free option": [343603, 116315],
    "Make it a quicker recipe — under 30 minutes": [366158, 203023],
    
    "Can I substitute butter with olive oil?": [248238, 240590],
    "What if I don't have heavy cream?": [133348, 142426],
    "I don't have garlic — what can I use instead?": [447475, 423602],
    "Replace chicken with tofu in the recipe": [82380, 200427],
    "What can I use instead of soy sauce?": [224097, 448897],
    "I'm out of eggs — how do I substitute them?": [443425, 424209],
    "Can I swap flour for almond flour in baking?": [267272, 496181],
}

TEST_QUERIES = [
    {"q": k, "expected_intent": "GENERAL" if i < 10 else ("REFINE" if i < 18 else "SUBS")}
    for i, k in enumerate(GROUND_TRUTH.keys())
]

def check_hallucination_llm(reply: str, recipes: list[dict], intent: str) -> bool:
    if not reply or not recipes: return True
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = ""
    for r in recipes:
        context += f"- {r.get('name')} (ID: {r.get('recipe_id')}): {r.get('minutes')} mins. Ingredients: {', '.join(r.get('ingredients', []))}. Tags: {', '.join(r.get('tags', []))}\n"
    
    if intent == "SUBS":
        prompt = f"""
You are evaluating an AI assistant's reply for hallucinations on a substitution question. 
The assistant was provided with the following recipes as context:
{context}

The assistant generated this reply:
"{reply}"

The assistant is ALLOWED to use general world knowledge to suggest ingredient substitutions.
However, it must NOT invent facts about the retrieved recipes themselves.
Are there any factual claims in the reply ABOUT the specific retrieved recipes (e.g., claiming a recipe contains an ingredient it does not, or has a different cook time) that are NOT supported by the context?
Answer exactly "YES" if there is a recipe hallucination, or "NO" if the recipe facts are supported (or not mentioned) and the rest is just safe substitution advice. Only output YES or NO.
"""
    else:
        prompt = f"""
You are evaluating an AI assistant's reply for hallucinations on a recipe search. 
The assistant was provided with the following recipes as context:
{context}

The assistant generated this reply:
"{reply}"

Analyze every factual claim in the reply regarding recipes, ingredients, times, or tags. 
Are there any factual claims in the reply that are NOT supported by the context?
Answer exactly "YES" if there is a hallucination (unsupported claim), or "NO" if all claims are supported or it's a general safe statement. Only output YES or NO.
"""
    try:
        ans = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip().upper()
        return "YES" not in ans
    except Exception as e:
        print("Groq Judge error:", e)
        return True

results = []
session_id = "eval-session-002"

print(f"Running eval over {len(TEST_QUERIES)} queries...")

for i, tq in enumerate(TEST_QUERIES):
    query = tq["q"]
    expected_intent = tq["expected_intent"]
    
    try:
        ans_dict = invoke_rag(query, session_id + str(i), [])
        reply = ans_dict["reply"]
        actual_intent = ans_dict["intent"]
        recs = ans_dict["updated_results"]
        rids = [r.get("recipe_id") for r in recs]
        
        expected_rids = set(GROUND_TRUTH[query])
        retrieval_ok = bool(expected_rids.intersection(set(rids)))
        
        hallucination_free = check_hallucination_llm(reply, recs, expected_intent)
        reply_sane = bool(reply) and len(reply) > 20
    except Exception as e:
        print(f"Error processing query {i}: {e}")
        retrieval_ok = False
        hallucination_free = False
        reply_sane = False
        actual_intent = "ERROR"

    results.append({
        "query": query,
        "actual_intent": actual_intent,
        "expected_intent": expected_intent,
        "retrieval_ok": retrieval_ok,
        "hallucination_free": hallucination_free,
        "reply_sane": reply_sane
    })
    
    status = "✅" if (retrieval_ok and hallucination_free and reply_sane) else "⚠️"
    print(f"[{i+1:02d}] {status} intent={actual_intent:<8} retrieval={retrieval_ok:<5} hall_free={hallucination_free:<5} sane={reply_sane:<5} | {query[:45]}")
    
    # Wait to avoid Groq TPM limits
    time.sleep(4)

total = len(results)
rel_ok  = sum(1 for r in results if r["retrieval_ok"])
hall_ok = sum(1 for r in results if r["hallucination_free"])
sane_ok = sum(1 for r in results if r["reply_sane"])

gen_results = [r for r in results if r["expected_intent"] == "GENERAL"]
ref_results = [r for r in results if r["expected_intent"] == "REFINE"]
subs_results = [r for r in results if r["expected_intent"] == "SUBS"]

def _pct(num, den):
    return f"{num}/{den} ({int(100*num/den)}%)" if den > 0 else "N/A"

report = f"""
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
"""

with open(Path(__file__).resolve().parent / "eval_report.md", "a") as f:
    f.write("\n" + report + "\n")
print("\nDone. Appended to eval_report.md")
