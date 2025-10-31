from fastapi import APIRouter, Query
from services.ocm import stations_in_bbox

router = APIRouter()

@router.get("/charging-stations")
async def stations_ep(
    bbox: str = Query(..., description="minLon,minLat,maxLon,maxLat"),
    maxresults: int = 80
):
    min_lon, min_lat, max_lon, max_lat = [float(x) for x in bbox.split(",")]
    data = await stations_in_bbox(min_lon, min_lat, max_lon, max_lat, maxresults=maxresults)
    return {"count": len(data), "items": data}
