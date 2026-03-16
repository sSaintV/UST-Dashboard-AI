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
    positive: float = Field(..., ge=0, le=100)
    neutral:  float = Field(..., ge=0, le=100)
    negative: float = Field(..., ge=0, le=100)
    faces:    int   = Field(..., ge=0)


class EmotionResponse(BaseModel):
    """Aggregated emotion state served to the Next.js frontend."""
    available:  bool          = Field(..., description="True when camera+model are operational or demo is active")
    demo:       bool          = False
    positive:   float         = Field(0.0,  ge=0, le=100)
    neutral:    float         = Field(100.0, ge=0, le=100)
    negative:   float         = Field(0.0,  ge=0, le=100)
    face_count: int           = Field(0, ge=0)
    fps:        float         = Field(0.0, ge=0)
    dominant:   str           = "neutral"
    history:    List[HistoryPoint] = []


@router.get("/emotion", response_model=EmotionResponse)
def get_emotion() -> EmotionResponse:
    """
    Returns the emotion snapshot aggregated over the last 60 seconds.
    Safe to poll every 2 s; results are held in a thread-safe in-memory dict.
    """
    state = emotion_service.get_state()
    return EmotionResponse(
        available=state.get("available", False),
        demo=state.get("demo", False),
        positive=state.get("positive", 0.0),
        neutral=state.get("neutral", 100.0),
        negative=state.get("negative", 0.0),
        face_count=state.get("face_count", 0),
        fps=state.get("fps", 0.0),
        dominant=state.get("dominant", "neutral"),
        history=[HistoryPoint(**h) for h in state.get("history", [])],
    )


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
