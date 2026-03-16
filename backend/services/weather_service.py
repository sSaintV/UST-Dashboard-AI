import httpx
import asyncio
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Cyberjaya Coordinates
LAT = 2.922
LON = 101.656

API_URL = "https://api.open-meteo.com/v1/forecast"

class WeatherService:
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._last_fetch = 0
        self._ttl = 900  # 15 minutes
        self._lock = asyncio.Lock()

    async def get_weather(self) -> Dict[str, Any]:
        """Fetch weather data from Open-Meteo with 15-min caching."""
        async with self._lock:
            now = time.time()
            if self._cache and (now - self._last_fetch < self._ttl):
                return self._cache

            params = {
                "latitude": LAT,
                "longitude": LON,
                "current_weather": "true",
                "hourly": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,uv_index",
                "timezone": "auto",
                "forecast_days": 2
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(API_URL, params=params, timeout=10.0)
                    response.raise_for_status()
                    data = response.json()
                    
                    self._cache = self._process_weather_data(data)
                    self._last_fetch = now
                    return self._cache
            except Exception as e:
                logger.error(f"Weather fetch failed: {e}")
                if self._cache:
                    return self._cache
                # Fallback data if API fails and no cache exists
                return self._get_fallback_data()

    def _process_weather_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format the relevant fields for the frontend."""
        current = data.get("current_weather", {})
        hourly = data.get("hourly", {})
        
        # We want the next 24 hours of forecast
        # Find the index of the current hour in the hourly data
        # (Simplified: just take the first 24 if they are sequential starting near now)
        # Open-Meteo usually starts from 00:00 of the current day.
        
        return {
            "current": {
                "temp": current.get("temperature"),
                "wind_speed": current.get("windspeed"),
                "wind_direction": current.get("winddirection"),
                "weather_code": current.get("weathercode"),
                "time": current.get("time")
            },
            "hourly": {
                "times": hourly.get("time", [])[:24],
                "temps": hourly.get("temperature_2m", [])[:24],
                "codes": hourly.get("weather_code", [])[:24],
                "humidity": hourly.get("relative_humidity_2m", [])[:24],
                "uv_index": hourly.get("uv_index", [])[:24]
            },
            "location": "Cyberjaya",
            "last_updated": time.time()
        }

    def _get_fallback_data(self) -> Dict[str, Any]:
        return {
            "current": {
                "temp": 28.5,
                "wind_speed": 5.2,
                "wind_direction": 180,
                "weather_code": 1,
                "time": "N/A"
            },
            "hourly": {
                "times": [],
                "temps": [],
                "codes": [],
                "humidity": [],
                "uv_index": []
            },
            "location": "Cyberjaya (Offline)",
            "last_updated": time.time()
        }

# Singleton
weather_service = WeatherService()
