import urllib.request, json, time, random

BASE = "http://127.0.0.1:8000"

def post(url, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        if hasattr(e, 'read'): print("Error:", e.read().decode())
        raise e

def get(url, token=None):
    headers = {}
    if token: headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

print("=== 1. SIGNUP ===")
# Generate a random email so the test can be run multiple times
email = f"test_{int(time.time())}@gmail.com"
pw = "TestPassword123!"
signup_res = post("/auth/signup", {"email": email, "password": pw, "display_name": "Test User", "dietary_tags": ["vegan"]})
print(signup_res)

print("\n=== 2. LOGIN ===")
# Supabase auth might take a second, or require email confirmation depending on settings.
# But we disabled email confirmation in typical Supabase local dev, let's assume it works.
time.sleep(1)
login_res = post("/auth/login", {"email": email, "password": pw})
print(f"Logged in. user_id: {login_res['user_id']}")
token = login_res["access_token"]
uid = login_res["user_id"]

print("\n=== 3. PANTRY ADD ===")
pantry_res = post(f"/pantry/{uid}", {"ingredient": "tofu"}, token)
print(pantry_res)
pantry_res2 = post(f"/pantry/{uid}", {"ingredient": "broccoli"}, token)
print(pantry_res2)

print("\n=== 4. FAVORITE ===")
fav_res = post(f"/favorites/{uid}", {"recipe_id": 149476}, token)  # Salmon and lemon
print(fav_res)

print("\n=== 5. MEAL PLAN GENERATE ===")
plan_res = post(f"/mealplan/{uid}/generate", {}, token)
print(f"Plan ID: {plan_res['meal_plan']['plan_id']}")
print(f"Total Slots: {len(plan_res['meal_plan']['slots'])}")
for slot in plan_res['meal_plan']['slots'][:3]:
    print(f"  Day {slot['day']} {slot['slot']}: {slot['name']} ({slot['recipe_id']})")
