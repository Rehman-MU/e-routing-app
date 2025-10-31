import httpx
from core.config import settings

async def autocomplete(query: str, limit: int = 5):
    url = f"{settings.PHOTON_BASE_URL}/api"
    params = {"q": query, "limit": limit}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    out = []
    for f in data.get("features", []):
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        label = props.get("name") or props.get("label") or props.get("street") or "Result"
        city = props.get("city") or props.get("county") or ""
        country = props.get("country") or ""
        display = ", ".join([x for x in [label, city, country] if x])
        if len(coords) == 2:
            out.append({"label": display, "coord": coords})
    return out
