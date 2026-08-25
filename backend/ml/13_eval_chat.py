import os, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

print("Imports done")
from app.services.rag_chain import invoke_rag
from groq import Groq

GROUND_TRUTH = {
    "Show me a quick chicken dinner for weeknights": [60301, 328828],
    "I want something with salmon and lemon": [149476, 127788],
    "What can I make with pasta and tomatoes?": [475231, 176435],
}

TEST_QUERIES = [
    {"q": k, "expected_intent": "GENERAL"}
    for i, k in enumerate(GROUND_TRUTH.keys())
]

def check_hallucination_llm(reply: str, recipes: list[dict]) -> bool:
    if not reply or not recipes: return True
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    context = ""
    for r in recipes:
        context += f"- {r.get('name')} (ID: {r.get('recipe_id')}): {r.get('minutes')} mins. Ingredients: {', '.join(r.get('ingredients', []))}. Tags: {', '.join(r.get('tags', []))}\n"
    
    prompt = f"Recipes:\\n{context}\\nReply:\\n{reply}\\nAre there any claims in the reply NOT in the context? Output YES or NO."
    print("Calling Groq for hallucination check...")
    try:
        ans = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        ).choices[0].message.content.strip().upper()
        return "YES" not in ans
    except Exception as e:
        print("Groq error:", e)
        return True

results = []
session_id = "eval-session-debug"
print("Starting queries...")
for i, tq in enumerate(TEST_QUERIES):
    query = tq["q"]
    print(f"Query {i}: {query}")
    ans_dict = invoke_rag(query, session_id + str(i), [])
    print(f"Got RAG response for {i}")
    reply = ans_dict["reply"]
    actual_intent = ans_dict["intent"]
    recs = ans_dict["updated_results"]
    rids = [r.get("recipe_id") for r in recs]
    expected_rids = set(GROUND_TRUTH[query])
    retrieval_ok = bool(expected_rids.intersection(set(rids)))
    hallucination_free = check_hallucination_llm(reply, recs)
    print(f"[{i}] done")
    
