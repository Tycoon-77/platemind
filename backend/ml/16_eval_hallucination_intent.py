"""
16_eval_hallucination_intent.py
Intent-aware hallucination eval: strict for GENERAL/REFINE, relaxed for SUBS.
Uses HTTP /chat endpoint and seeded sessions for REFINE/SUBS.
"""
import os, sys, json, time, uuid, urllib.request
from pathlib import Path
sys.path.insert(0, "/Users/keerthanbs/Self Improvement/PROJECTS/platemind/backend")
from dotenv import load_dotenv
load_dotenv("/Users/keerthanbs/Self Improvement/PROJECTS/platemind/backend/.env")
from groq import Groq

BASE = "http://127.0.0.1:8000"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

GROUND_TRUTH = {
    "Show me a quick chicken dinner for weeknights":    [],
    "I want something with salmon and lemon":           [],
    "What can I make with pasta and tomatoes?":         [],
    "Give me a hearty beef stew recipe":                [],
    "Something with shrimp and garlic":                 [],
    "I want a breakfast egg dish":                      [],
    "Find me a soup with vegetables":                   [],
    "What is a good chocolate dessert?":                [],
    "Show me Indian spiced dishes":                     [],
    "I want a salad with avocado":                      [],
    # REFINE
    "Make it vegetarian":                               [],
    "Only show me recipes under 20 minutes":            [],
    "I need something gluten free":                     [],
    "Something simpler and less spicy please":          [],
    "Lower calorie version please":                     [],
    "Can you make it vegan?":                           [],
    "I need a dairy free option":                       [],
    "Make it a quicker recipe — under 30 minutes":      [],
    # SUBS
    "Can I substitute butter with olive oil?":          [],
    "What if I don't have heavy cream?":                [],
    "I don't have garlic — what can I use instead?":    [],
    "Replace chicken with tofu in the recipe":          [],
    "What can I use instead of soy sauce?":             [],
    "I'm out of eggs — how do I substitute them?":      [],
    "Can I swap flour for almond flour in baking?":     [],
}
QUERIES = list(GROUND_TRUTH.keys())
GENERAL = QUERIES[:10]
REFINE  = QUERIES[10:18]
SUBS    = QUERIES[18:]

SEED_FOR = {}
for i, q in enumerate(REFINE):
    SEED_FOR[q] = GENERAL[i % 10]
for i, q in enumerate(SUBS):
    SEED_FOR[q] = GENERAL[(len(REFINE) + i) % 10]

def chat(query, session_id):
    body = json.dumps({"session_id": session_id, "message": query}).encode()
    req = urllib.request.Request(
        BASE + "/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def judge(reply, recipes, intent):
    if not reply or not recipes:
        return False, "SKIP"
    
    context = ""
    for r in recipes:
        context += (
            f"- {r.get('name')} ({r.get('minutes')} mins). "
            f"Ingredients: {', '.join(r.get('ingredients', [])[:10])}. "
            f"Tags: {', '.join(r.get('tags', [])[:6])}\n"
        )
    
    if intent in ("GENERAL", "REFINE"):
        prompt = f"""\
You are evaluating an AI reply for hallucinations.
The assistant was given ONLY these recipes as context:
{context}

Assistant reply:
"{reply}"

Does the reply state any ingredient, cook time, tag, calorie, or cooking step NOT in the context?
Answer exactly YES (hallucination) or NO (fully grounded). One word only."""
    else:
        prompt = f"""\
You are evaluating an AI reply for hallucinations regarding specific recipes.
The assistant was given ONLY these recipes as context:
{context}

Assistant reply:
"{reply}"

The assistant is ALLOWED to use general culinary knowledge for substitution advice.
However, examine any claims attributed specifically to the retrieved recipes (e.g. naming a recipe and stating its ingredients, cook time, or tags).
- If the reply fabricates or invents specific details about the recipes in the context that are not actually there, answer YES (hallucination).
- If the reply only uses accurate facts from the context when discussing the specific recipes, and uses valid general knowledge for the substitutions, answer NO.
Output exactly one word: YES or NO."""

    try:
        ans = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        ).choices[0].message.content.strip().upper()
        return ("YES" not in ans), ans
    except Exception as e:
        print(f"  judge error: {e}", flush=True)
        return False, "ERR"

print(f"Hallucination eval (intent-aware judge) — {len(QUERIES)} queries\n", flush=True)
print(f"{'#':>3}  {'OK':>4}  {'Intent':<8}  {'Judge':>5}  Query", flush=True)
print("-" * 78, flush=True)

results = []
seed_cache = {}

for i, query in enumerate(QUERIES):
    intent_type = "GENERAL" if i < 10 else ("REFINE" if i < 18 else "SUBS")
    try:
        if intent_type == "GENERAL":
            sid = str(uuid.uuid4())
            resp = chat(query, sid)
            seed_cache[query] = (sid, resp.get("reply", ""))
        else:
            seed_q = SEED_FOR[query]
            if seed_q in seed_cache:
                sid, _ = seed_cache[seed_q]
            else:
                sid = str(uuid.uuid4())
                chat(seed_q, sid)
                seed_cache[seed_q] = (sid, "")
                time.sleep(2)
            resp = chat(query, sid)
            
        reply   = resp.get("reply", "")
        recipes = resp.get("updated_results", [])
        actual_intent = resp.get("intent", intent_type)
        ok, verdict = judge(reply, recipes, actual_intent)
    except Exception as e:
        print(f"  HTTP error: {e}", flush=True)
        ok, verdict, actual_intent = False, "ERR", "ERR"

    results.append({"query": query, "ok": ok, "type": intent_type, "verdict": verdict})
    icon = "✅" if ok else "❌"
    print(f"{i+1:>3}  {icon}  {actual_intent:<8}  {verdict:<5}  {query[:50]}", flush=True)
    time.sleep(4)

total = len(results)
hits = sum(1 for r in results if r["ok"])
g_hits = sum(1 for r in results if r["ok"] and r["type"] == "GENERAL")
rf_hits = sum(1 for r in results if r["ok"] and r["type"] == "REFINE")
sb_hits = sum(1 for r in results if r["ok"] and r["type"] == "SUBS")

pct = 100 * hits // total if total else 0

print("\n" + "=" * 78, flush=True)
print(f"Hallucination-free: {hits}/{total} ({pct}%)", flush=True)
print(f"  GENERAL:  {g_hits}/10", flush=True)
print(f"  REFINE:   {rf_hits}/8", flush=True)
print(f"  SUBS:     {sb_hits}/7", flush=True)
print("=" * 78, flush=True)

rp = Path("/Users/keerthanbs/Self Improvement/PROJECTS/platemind/backend/ml/eval_report.md")
with open(rp, "a") as f:
    f.write(
        f"\n### Hallucination re-eval — intent-aware judge & prompt\n"
        f"- **Hallucination-free**: {hits}/{total} ({pct}%)\n"
        f"  - GENERAL: {g_hits}/10  |  REFINE: {rf_hits}/8  |  SUBS: {sb_hits}/7\n"
    )
print(f"Appended to {rp}", flush=True)
