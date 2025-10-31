import httpx, polyline
from core.config import settings

async def route(start_lon, start_lat, end_lon, end_lat, profile="driving"):
    base = settings.OSRM_BASE_URL.rstrip("/")
    coords = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    url = f"{base}/route/v1/{profile}/{coords}"
    params = {"overview": "full", "geometries": "polyline", "steps": "false"}
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    routes = data.get("routes", [])
    if not routes:
        return None
    r0 = routes[0]
    distance_km = r0["distance"] / 1000.0
    duration_min = r0["duration"] / 60.0
    pts = polyline.decode(r0["geometry"])  # list of (lat, lon)
    # convert to GeoJSON-like LineString
    line_coords = [[lon, lat] for lat, lon in pts]
    return {"distance_km": distance_km, "duration_min": duration_min,
            "line": {"type": "LineString", "coordinates": line_coords}}
