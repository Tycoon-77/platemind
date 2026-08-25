import re
path = "backend/app/routers/recipes.py"
with open(path, "r") as f:
    text = f.read()

import_statement = "import httpx\nimport re\nfrom fastapi.responses import RedirectResponse\nfrom fastapi import APIRouter"
text = text.replace("from fastapi import APIRouter", import_statement)

endpoint = """
_image_cache = {}

@router.get("/{recipe_id}/image")
async def get_recipe_image(recipe_id: int):
    if recipe_id in _image_cache:
        return RedirectResponse(url=_image_cache[recipe_id])

    url = f"https://www.food.com/recipe/test-{recipe_id}"
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200:
                match = re.search(r'<meta name="og:image" content="(.*?)"', resp.text)
                if match:
                    img_url = match.group(1)
                    # Reject food.com default placeholders
                    if "gk-static" not in img_url and "default" not in img_url:
                        _image_cache[recipe_id] = img_url
                        return RedirectResponse(url=img_url)
    except Exception as e:
        print(f"Scrape error: {e}")
        
    fallback = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400&q=80"
    return RedirectResponse(url=fallback)

@router.get("/{recipe_id}")
"""

text = text.replace("@router.get(\"/{recipe_id}\")", endpoint)

with open(path, "w") as f:
    f.write(text)
