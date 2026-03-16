from fastapi import APIRouter
from services.news_service import news_service

router = APIRouter(prefix="/news", tags=["news"])

@router.get("")
async def get_news():
    """Returns curated UST internal announcements."""
    return {"items": news_service.get_news()}
