import httpx
from core.config import settings

async def stations_in_bbox(min_lon, min_lat, max_lon, max_lat, maxresults=100):
    params = {
        "output": "json",
        "countrycode": "DE",
        "boundingbox": f"{min_lat},{min_lon},{max_lat},{max_lon}",
        "maxresults": maxresults,
    }
    headers = {"User-Agent": "ev-routing-prototype/0.1"}
    if settings.OCM_API_KEY:
        headers["X-API-Key"] = settings.OCM_API_KEY

    async with httpx.AsyncClient(timeout=20, headers=headers) as client:
        r = await client.get(settings.OCM_BASE_URL, params=params)
        r.raise_for_status()
        raw = r.json()

    out = []
    for row in raw:
        addr = row.get("AddressInfo", {})
        conn = (row.get("Connections") or [{}])[0]
        power_kw = conn.get("PowerKW") or 22
        out.append({
            "ocm_id": row.get("ID"),
            "name": addr.get("Title"),
            "lon": addr.get("Longitude"),
            "lat": addr.get("Latitude"),
            "power_kw": power_kw,
            "network": (row.get("OperatorInfo") or {}).get("Title"),
        })
    return out
