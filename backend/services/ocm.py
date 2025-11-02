# backend/services/ocm.py
import httpx
from typing import List, Dict, Tuple
from core.config import settings

OCM_URL = settings.OCM_BASE_URL.rstrip("/")

async def _ocm_query(lat: float, lon: float, radius_km: float, maxresults: int = 80) -> List[Dict]:
    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lon,
        "distance": radius_km,
        "distanceunit": "KM",
        "maxresults": maxresults,
        "compact": "true",
        "verbose": "false",
        "countrycode": "DE",  # focus on Germany for now
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(f"{OCM_URL}", params=params)
        if r.status_code != 200:
            return []
        return r.json()

def _slim(rec: Dict) -> Dict:
    addr = rec.get("AddressInfo") or {}
    stat = (rec.get("Connections") or [{}])[0]
    return {
        "ocm_id": rec.get("ID"),
        "name": addr.get("Title") or "Charger",
        "lon": addr.get("Longitude"),
        "lat": addr.get("Latitude"),
        "power_kw": stat.get("PowerKW"),
    }

def _sample_indices(n: int, k: int) -> List[int]:
    if n <= k:
        return list(range(n))
    step = max(1, n // k)
    return list(range(0, n, step))

async def stations_along_line(line_coords: List[List[float]],
                              radius_km: float = 7.0,
                              max_per_call: int = 80,
                              approx_calls: int = 12) -> List[Dict]:
    """
    Sample ~approx_calls points along the route and query OCM around each.
    Deduplicate by OCM ID. Returns slim charger dicts.
    """
    idxs = _sample_indices(len(line_coords), approx_calls)
    seen = set()
    out: List[Dict] = []
    for i in idxs:
        lon, lat = line_coords[i]
        try:
            batch = await _ocm_query(lat, lon, radius_km, maxresults=max_per_call)
        except httpx.RequestError:
            batch = []
        for rec in batch:
            slim = _slim(rec)
            if not (slim["lon"] and slim["lat"]):
                continue
            oid = slim["ocm_id"]
            if oid in seen:
                continue
            seen.add(oid)
            out.append(slim)
    return out
