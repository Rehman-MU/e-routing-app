from fastapi import APIRouter
from pydantic import BaseModel
from services.osrm import route as osrm_route

router = APIRouter()

class RouteIn(BaseModel):
    start: list[float]  # [lon, lat]
    end: list[float]
    profile: str = "driving"

@router.post("/route")
async def route_ep(body: RouteIn):
    res = await osrm_route(body.start[0], body.start[1], body.end[0], body.end[1], body.profile)
    if not res:
        return {"error": "NoRoute"}
    return res
