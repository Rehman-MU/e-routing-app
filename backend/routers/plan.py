from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points
from services.osrm import route as osrm_route
from services.ocm import stations_in_bbox
from db import get_db
from sqlalchemy.orm import Session
from models import Query as MQuery, Plan as MPlan, Vehicle as MVehicle
import math

router = APIRouter()

class PlanIn(BaseModel):
    start: list[float] = Field(..., description="[lon,lat]")
    end: list[float]   = Field(..., description="[lon,lat]")
    start_soc: float = 80
    arrival_soc: float = 20
    vehicle_id: int

class PlanOut(BaseModel):
    fastest: dict
    cheapest: dict

def soc_needed(distance_km: float, km_per_soc: float) -> float:
    return distance_km / km_per_soc  # in percentage points

def charge_time_min(delta_soc: float, rate_soc_per_min: float) -> float:
    return max(0.0, delta_soc) / rate_soc_per_min

def bbox_around_line(line_coords: list[list[float]], buffer_km: float = 5.0):
    # naive bbox with buffer
    lons = [p[0] for p in line_coords]; lats = [p[1] for p in line_coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    # ~ rough degree buffer (not exact): 1 deg lat ≈ 111 km, lon ≈ 111*cos(lat) km
    mid_lat = sum(lats)/len(lats)
    dlat = buffer_km/111.0
    dlon = buffer_km/(111.0*max(0.2, math.cos(math.radians(mid_lat))))
    return (min_lon-dlon, min_lat-dlat, max_lon+dlon, max_lat+dlat)

def plan_one_stop(route_km: float, start_soc: float, arrival_soc: float, veh: MVehicle, candidates: list[dict]):
    """Greedy: pick the candidate closest to the mid-point in distance along the path."""
    # Required SOC to drive whole route
    need_total = soc_needed(route_km, veh.consumption_km_per_soc)
    if start_soc - need_total >= arrival_soc:
        # no stop
        return {"stops": [], "charge_min": 0.0}

    # if one stop can help: target to leave charger with enough SOC to finish with arrival_soc
    delta_needed = arrival_soc + need_total - start_soc
    if delta_needed <= 100:  # feasible within 0..100
        # pick any “reasonable” charger; in practice select the closest to the route midpoint
        if not candidates:
            return None
        # simple pick: highest power among top 10
        top = sorted(candidates, key=lambda x: - (x["power_kw"] or 0))[:10]
        chosen = top[0]
        charge_min = charge_time_min(delta_needed, veh.charge_rate_soc_per_min)
        return {"stops": [chosen], "charge_min": charge_min}

    # otherwise two stops heuristic
    if len(candidates) < 2:
        return None
    chosen = sorted(candidates, key=lambda x: -(x["power_kw"] or 0))[:2]
    # split charge equally (very rough)
    per_stop_soc = delta_needed / 2.0
    charge_min = sum(charge_time_min(per_stop_soc, veh.charge_rate_soc_per_min) for _ in chosen)
    return {"stops": chosen, "charge_min": charge_min}

@router.post("/ev-plan", response_model=PlanOut)
async def ev_plan_ep(body: PlanIn, db: Session = Depends(get_db)):
    veh = db.query(MVehicle).filter(MVehicle.id == body.vehicle_id).first()
    if not veh:
        raise ValueError("vehicle not found")

    r = await osrm_route(body.start[0], body.start[1], body.end[0], body.end[1])
    if not r:
        return {"fastest": {"error": "NoRoute"}, "cheapest": {"error": "NoRoute"}}

    route_km = r["distance_km"]
    line = r["line"]

    # save query
    q = MQuery(
        start_lon=body.start[0], start_lat=body.start[1],
        end_lon=body.end[0], end_lat=body.end[1],
        start_soc=body.start_soc, arrival_soc=body.arrival_soc,
        vehicle_id=veh.id
    )
    db.add(q); db.commit(); db.refresh(q)

    # stations near route
    bbox = bbox_around_line(line["coordinates"], buffer_km=7.5)
    ocm = await stations_in_bbox(*bbox, maxresults=120)
    # naive filter: within 5km of the polyline
    ls = LineString(line["coordinates"])
    candidates = []
    for s in ocm:
        p = Point(s["lon"], s["lat"])
        if ls.distance(p) <= 0.05:  # ~5 km rough in degrees
            candidates.append(s)

    scheme = plan_one_stop(route_km, body.start_soc, body.arrival_soc, veh, candidates)

    # times
    drive_min = r["duration_min"]
    charge_min = (scheme or {}).get("charge_min", 0.0)
    total_fastest = drive_min + charge_min
    # “cheapest” == assume we prefer slower AC if available: add +30% charge time if only low-power
    slow_factor = 1.3 if all((st.get("power_kw", 0) <= 22) for st in (scheme or {}).get("stops", [])) else 1.0
    total_cheapest = drive_min + charge_min * slow_factor

    fastest = {
        "summary": {"drive_min": drive_min, "charge_min": charge_min, "total_time_min": total_fastest},
        "route": r["line"], "stops": (scheme or {}).get("stops", [])
    }
    cheapest = {
        "summary": {"drive_min": drive_min, "charge_min": charge_min*slow_factor, "total_time_min": total_cheapest},
        "route": r["line"], "stops": (scheme or {}).get("stops", [])
    }

    # store plans (optional)
    db.add_all([
        MPlan(query_id=q.id, plan_type="fastest", total_time_min=fastest["summary"]["total_time_min"], total_cost_eur=None, route_geojson=fastest["route"], steps=fastest),
        MPlan(query_id=q.id, plan_type="cheapest", total_time_min=cheapest["summary"]["total_time_min"], total_cost_eur=None, route_geojson=cheapest["route"], steps=cheapest),
    ])
    db.commit()

    return {"fastest": fastest, "cheapest": cheapest}
