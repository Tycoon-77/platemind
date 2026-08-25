"""
14_eval_hallucination.py — Hallucination-only re-eval after system prompt tightening.
"""
import os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import importlib
import app.services.rag_chain as _rc_mod
importlib.reload(_rc_mod)
invoke_rag = _rc_mod.invoke_rag

from groq import Groq

ALL_QUERIES = [
    "Show me a quick chicken dinner for weeknights",
    "I want something with salmon and lemon",
    "What can I make with pasta and tomatoes?",
    "Give me a hearty beef stew recipe",
    "Something with shrimp and garlic",
    "I want a breakfast egg dish",
    "Find me a soup with vegetables",
    "What is a good chocolate dessert?",
    "Show me Indian spiced dishes",
    "I want a salad with avocado",
    "Make it vegetarian",
    "Only show me recipes under 20 minutes",
    "I need something gluten free",
    "Something simpler and less spicy please",
    "Lower calorie version please",
    "Can you make it vegan?",
    "I need a dairy free option",
    "Make it a quicker recipe — under 30 minutes",
    "Can I substitute butter with olive oil?",
    "What if I don't have heavy cream?",
    "I don't have garlic — what can I use instead?",
    "Replace chicken with tofu in the recipe",
    "What can I use instead of soy sauce?",
    "I'm out of eggs — how do I substitute them?",
    "Can I swap flour for almond flour in baking?",
]

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def check_hallucination(reply: str, recipes: list) -> tuple:
    if not reply or not recipes:
        return False, "SKIP"

    context = ""
    for r in recipes:
        context += (
            f"- {r.get('name')} (ID: {r.get('recipe_id')}, {r.get('minutes')} mins). "
            f"Ingredients: {', '.join(r.get('ingredients', []))}. "
            f"Tags: {', '.join(r.get('tags', []))}\n"
        )

    prompt = f"""\
You are evaluating an AI assistant's reply for hallucinations.
The assistant was given ONLY the following recipes as its factual context:
{context}

The assistant's reply:
"{reply}"

Examine every factual claim about recipe names, ingredient lists, cook times, tags, \
calories, quantities, or cooking steps.
- If the reply states any fact that is NOT present in the context above, answer YES (hallucination).
- If every factual claim is supported by the context, or the reply is a safe general statement, answer NO.
Output exactly one word: YES or NO."""

    try:
        ans = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        ).choices[0].message.content.strip().upper()
        return ("YES" not in ans), ans
    except Exception as e:
        print(f"  Judge error: {e}")
        return True, "ERROR"


print(f"Running hallucination-only eval on {len(ALL_QUERIES)} queries...\n")
print(f"{'#':>3}  {'Hall-free':>9}  {'Judge':>5}  Query")
print("-" * 72)

total = 0
hall_ok = 0

for i, query in enumerate(ALL_QUERIES):
    try:
        result  = invoke_rag(query, f"halleval-{i}", [])
        reply   = result["reply"]
        recipes = result["updated_results"]
        ok, judge_ans = check_hallucination(reply, recipes)
    except Exception as e:
        print(f"  RAG error: {e}")
        ok, judge_ans = False, "ERROR"

    total += 1
    if ok:
        hall_ok += 1

    icon = "✅" if ok else "❌"
    print(f"{i+1:>3}  {icon} {str(ok):>7}   {judge_ans:<5}  {query[:55]}")
    time.sleep(4)

pct = 100 * hall_ok // total if total else 0
print("\n" + "=" * 72)
print(f"Hallucination-free: {hall_ok}/{total} ({pct}%)")
print("=" * 72)

report_line = (
    f"\n### Hallucination re-eval (grounded system prompt)\n"
    f"- **Hallucination-free**: {hall_ok}/{total} ({pct}%)\n"
)
report_path = Path(__file__).resolve().parents[1] / "ml/eval_report.md"
with open(report_path, "a") as f:
    f.write(report_line)
print(f"Result appended to {report_path}")
