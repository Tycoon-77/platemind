import urllib.request
import json
def fetch(url, data=None):
    req = urllib.request.Request(url, method='GET' if data is None else 'POST')
    if data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

print("=== 1. GET /recipes/137739 ===")
r = fetch('http://127.0.0.1:8000/recipes/137739')
print(json.dumps(r, indent=2)[:500])

print("\n=== 2. GET /recipes/search?q=chicken ===")
r = fetch('http://127.0.0.1:8000/recipes/search?q=chicken')
print(json.dumps(r, indent=2)[:500])

print("\n=== 3. POST /recommend/pantry ===")
r = fetch('http://127.0.0.1:8000/recommend/pantry', data={"user_id": 1, "ingredients": ["chicken", "garlic", "onion"]})
print(json.dumps(r, indent=2)[:500])

print("\n=== 4. POST /recommend/hybrid ===")
r = fetch('http://127.0.0.1:8000/recommend/hybrid', data={"user_id": 1})
print(json.dumps(r, indent=2)[:500])

