from fastapi import APIRouter, HTTPException
from services.weather_service import weather_service

router = APIRouter(prefix="/weather", tags=["weather"])

@router.get("")
async def get_weather():
    """Returns current and 24h forecast weather for Cyberjaya."""
    try:
        data = await weather_service.get_weather()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
