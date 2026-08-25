import urllib.request
import json
def fetch(url, data=None):
    req = urllib.request.Request(url, method='GET' if data is None else 'POST')
    if data:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

r = fetch('http://127.0.0.1:8000/recommend/pantry', data={"user_id": 1, "ingredients": ["chicken", "garlic", "onion"]})
print(json.dumps(r['results'][0], indent=2)[:1000])
