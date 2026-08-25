import asyncio
from app.routers.recommend import recommend_from_pantry, PantryRecommendRequest
from app.ml_state import init_ml_state

async def main():
    init_ml_state()
    req = PantryRecommendRequest(user_id=1, ingredients=["chicken", "garlic", "onion"])
    try:
        res = await recommend_from_pantry(req)
        print("SUCCESS!")
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
