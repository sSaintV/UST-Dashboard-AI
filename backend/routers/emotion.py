"""
GET /api/emotion — returns the current aggregated emotion window state.

Input validation: read-only endpoint, no user-supplied parameters.
Response is validated and serialised through Pydantic.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List

from services.emotion_service import emotion_service

router = APIRouter(tags=["emotion"])


class HistoryPoint(BaseModel):
    """Single sparkline data-point (one inference cycle ~2 s apart)."""
    ts:       float = Field(..., description="Unix timestamp")
    faces:    int   = Field(..., ge=0)
    positive: float = 0.0
    neutral:  float = 100.0
    negative: float = 0.0
    emotions: dict[str, float] = Field(default_factory=dict)


class EmotionResponse(BaseModel):
    """Aggregated emotion state served to the Next.js frontend."""
    available:  bool          = Field(..., description="True when camera+model are operational or demo is active")
    demo:       bool          = False
    positive:   float         = 0.0
    neutral:    float         = 100.0
    negative:   float         = 0.0
    face_count: int           = 0
    fps:        float         = 0.0
    dominant:   str           = "neutral"
    emotions:   dict[str, float] = Field(default_factory=dict)
    history:    List[HistoryPoint] = []


@router.get("/emotion", response_model=EmotionResponse)
def get_emotion() -> EmotionResponse:
    """
    Returns the emotion snapshot aggregated over the last 60 seconds.
    Safe to poll every 2 s; results are held in a thread-safe in-memory dict.
    """
    state = emotion_service.get_state()
    return EmotionResponse(**state)


@router.get("/emotion/feed")
def video_feed():
    """
    Streams the live camera feed (with bounding boxes) as an MJPEG stream.
    Can be used directly in an HTML <img> tag's src attribute.
    """
    return StreamingResponse(
        emotion_service.get_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
