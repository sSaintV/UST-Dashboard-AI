"""
UST Reception AI Insight Dashboard — FastAPI backend.

Security notes:
- Binds to 127.0.0.1 only; never exposed on 0.0.0.0.
- CORS restricted to http://localhost:3000.
- No camera frames or biometric data are logged or stored.
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from services.emotion_service  import emotion_service
from services.footfall_service import footfall_service
from routers import emotion, weather, news, footfall

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on startup; clean up on shutdown."""
    logger.info("Starting EmotionService background thread…")
    emotion_service.start()
    logger.info("Starting FootfallService background thread…")
    footfall_service.start()
    yield
    # Background thread is daemon — OS will clean it up on process exit.
    logger.info("Shutting down.")


app = FastAPI(
    title="UST Reception AI Dashboard API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",   # Swagger UI available at /docs for dev
    redoc_url=None,
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Only allow the Next.js dev server on localhost to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(emotion.router,   prefix="/api")
app.include_router(weather.router,   prefix="/api")
app.include_router(news.router,      prefix="/api")
app.include_router(footfall.router,  prefix="/api")


@app.get("/health", tags=["meta"])
def health():
    """Simple liveness probe."""
    return {"status": "ok"}
