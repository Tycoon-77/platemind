"""
Manual test client for POST /chat multi-turn exchanges.
Run: python3 backend/test_chat_client.py
"""
import urllib.request
import json
import uuid

BASE = "http://127.0.0.1:8000"
SESSION = str(uuid.uuid4())

def chat(message: str, session_id: str = SESSION):
    req = urllib.request.Request(
        f"{BASE}/chat",
        data=json.dumps({"session_id": session_id, "message": message, "user_id": 1}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def print_turn(label, msg, result):
    print(f"\n{'='*60}")
    print(f"[{label}] USER: {msg}")
    print(f"        INTENT: {result.get('intent', '?')}")
    print(f"        CACHED: {result.get('from_cache', False)}")
    n = len(result.get('retrieved_recipe_ids', []))
    print(f"        RETRIEVED: {n} recipes")
    print(f"        REPLY: {result.get('reply', result.get('error', ''))[:400]}")
    if result.get("updated_results"):
        top3 = result["updated_results"][:3]
        print(f"        TOP RESULTS:")
        for r in top3:
            print(f"          • {r['name']} ({r['minutes']} min)")

# ─── Conversation 1: pantry-first discovery ──────────────────────────────
print("\n" + "="*60)
print("CONVERSATION 1: General discovery → refine → substitution")
print("="*60)

r = chat("I want a quick chicken dinner with garlic and lemon")
print_turn("1a", "quick chicken dinner with garlic and lemon", r)

r = chat("Make it under 30 minutes", SESSION)
print_turn("1b", "Make it under 30 minutes", r)

r = chat("What if I don't have fresh lemon? Can I substitute?", SESSION)
print_turn("1c", "What if I don't have fresh lemon?", r)

# ─── Conversation 2: dietary + substitution ───────────────────────────────
SESSION2 = str(uuid.uuid4())
print("\n" + "="*60)
print("CONVERSATION 2: Vegan + dietary")
print("="*60)

r = chat("Show me vegan pasta dishes", SESSION2)
print_turn("2a", "Show me vegan pasta dishes", SESSION2)
print_turn("2a", "Show me vegan pasta dishes", r)

r = chat("I need it gluten free too", SESSION2)
print_turn("2b", "I need it gluten free too", r)

print("\n\nAll turns complete.")
