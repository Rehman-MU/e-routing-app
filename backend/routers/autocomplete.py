from fastapi import APIRouter, Query
from services.photon import autocomplete

router = APIRouter()

@router.get("/autocomplete")
async def autocomplete_ep(q: str = Query(..., min_length=2), limit: int = 5):
    return await autocomplete(q, limit)
