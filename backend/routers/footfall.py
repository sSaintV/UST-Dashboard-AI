from fastapi import APIRouter
from services.footfall_service import footfall_service

router = APIRouter(prefix="/footfall", tags=["footfall"])

@router.get("")
async def get_footfall():
    """Returns real-time footfall / visitor intelligence data."""
    return footfall_service.get_state()
