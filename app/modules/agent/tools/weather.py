import os
import requests
import logging
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
from langchain_core.tools import tool
from app.modules.agent.schemas import WeatherResult

logger = logging.getLogger("agrimind.weather")

# Geographical coordinates for major agricultural districts & hubs in India
DISTRICT_COORDINATES: Dict[str, Tuple[float, float]] = {
    "mandya": (12.5238, 76.8988),
    "hyderabad": (17.3850, 78.4867),
    "rangareddy": (17.2403, 78.4294),
    "guntur": (16.3067, 80.4365),
    "karnal": (29.6857, 76.9905),
    "khanna": (30.7025, 76.2215),
    "rajkot": (22.3039, 70.8022),
    "indore": (22.7196, 75.8577),
    "nagpur": (21.1458, 79.0882),
    "nashik": (19.9975, 73.7898),
    "pune": (18.5204, 73.8567),
    "varanasi": (25.3176, 82.9739),
    "lucknow": (26.8467, 80.9462),
    "patna": (25.5941, 85.1376),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946)
}

def resolve_location_coordinates(location_str: str) -> Tuple[float, float, str]:
    """Resolves city or district name to (latitude, longitude, clean_name)."""
    clean_loc = location_str.lower().strip()
    for key, coords in DISTRICT_COORDINATES.items():
        if key in clean_loc:
            return coords[0], coords[1], key.capitalize()
    # Default to Mandya / South-Central India coordinates if unknown
    return 12.5238, 76.8988, location_str.split(",")[0].capitalize()

def fetch_open_meteo_live_weather(lat: float, lon: float, location_name: str) -> Optional[WeatherResult]:
    """
    Fetches genuine real-time live meteorological data from Open-Meteo API.
    Requires NO API key, verified public scientific source.
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code",
            "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Kolkata"
        }
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            curr = data.get("current", {})
            daily = data.get("daily", {})

            temp = curr.get("temperature_2m", 28.0)
            humidity = int(curr.get("relative_humidity_2m", 60))
            rain_mm = curr.get("precipitation", 0.0)
            wind_kmh = curr.get("wind_speed_10m", 10.0)
            
            prob_list = daily.get("precipitation_probability_max", [])
            rain_prob = prob_list[0] if prob_list else (75 if rain_mm > 0 else 15)

            # Map WMO weather codes to farmer-friendly conditions
            code = curr.get("weather_code", 0)
            if code == 0:
                forecast_desc = "Clear sunny skies"
            elif code in [1, 2]:
                forecast_desc = "Partly cloudy with pleasant sunlight"
            elif code == 3:
                forecast_desc = "Overcast cloudy skies"
            elif code in [51, 53, 55, 61, 63, 65]:
                forecast_desc = "Showers / Rain precipitation active"
            elif code in [95, 96, 99]:
                forecast_desc = "Thunderstorm with turbulent wind"
            else:
                forecast_desc = "Fair weather with scattered clouds"

            # Compute agronomic chemical spray window (Delta T = dry bulb - wet bulb approx.)
            if rain_mm > 2.0 or rain_prob > 70:
                advisory = f"High rainfall risk ({rain_prob}% prob, {rain_mm} mm). Postpone pesticide/fertilizer spraying to avoid chemical runoff."
            elif temp > 34.0:
                advisory = f"High temperature ({temp}°C) creates thermal stress. Irrigate in early morning or late evening; avoid midday chemical sprays."
            elif wind_kmh > 20.0:
                advisory = f"High wind speeds ({wind_kmh} km/h). Severe droplet drift hazard for foliar spraying."
            else:
                advisory = "Optimal weather window for foliar nutrient sprays, weeding, and routine crop field maintenance."

            return WeatherResult(
                location=f"{location_name}, India",
                temperature_c=round(temp, 1),
                humidity_percent=humidity,
                rainfall_mm=round(rain_mm, 1),
                rainfall_prob_percent=rain_prob,
                wind_speed_kmh=round(wind_kmh, 1),
                forecast=forecast_desc,
                agricultural_advisory=advisory,
                source="Open-Meteo Live Meteorology",
                retrieved_at=datetime.utcnow(),
                is_mock=False
            )
    except Exception as e:
        logger.warning(f"Open-Meteo live lookup failed: {str(e)}")
        return None

def get_weather_forecast(location: str = "Mandya, India") -> WeatherResult:
    """
    Fetches real-time weather information:
    1. If OPENWEATHER_API_KEY is configured, calls OpenWeatherMap API (raises RuntimeError on failure).
    2. If OPENWEATHER_API_KEY is absent, returns transparent DEMO / MOCK weather payload.
    """
    clean_location = location.strip() if location else "Mandya, India"
    lat, lon, resolved_city = resolve_location_coordinates(clean_location)

    # 1. Check OpenWeatherMap API if key is configured
    owm_key = os.getenv("OPENWEATHER_API_KEY", "").strip() or os.getenv("WEATHER_API_KEY", "").strip()
    if owm_key and not owm_key.startswith("your_"):
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": clean_location, "units": "metric", "appid": owm_key}
            res = requests.get(url, params=params, timeout=5)
            if res.status_code != 200:
                logger.error(f"OpenWeatherMap API error HTTP {res.status_code}: {res.text}")
                raise RuntimeError(f"OpenWeatherMap API error HTTP {res.status_code}")

            data = res.json()
            temp = data.get("main", {}).get("temp", 26.0)
            humidity = data.get("main", {}).get("humidity", 60)
            wind_speed_ms = data.get("wind", {}).get("speed", 3.0)
            wind_kmh = round(wind_speed_ms * 3.6, 1)
            rain_mm = data.get("rain", {}).get("1h", 0.0)
            desc = data.get("weather", [{}])[0].get("description", "Clear").capitalize()

            advisory = (
                "Optimal weather for farm operations." if rain_mm == 0
                else f"Rainfall detected ({rain_mm} mm). Hold foliar spraying."
            )

            return WeatherResult(
                location=data.get("name", clean_location),
                temperature_c=temp,
                humidity_percent=humidity,
                rainfall_mm=rain_mm,
                rainfall_prob_percent=75 if rain_mm > 0 else 20,
                wind_speed_kmh=wind_kmh,
                forecast=desc,
                agricultural_advisory=advisory,
                source="OpenWeatherMap",
                retrieved_at=datetime.utcnow(),
                is_mock=False
            )
        except requests.RequestException as req_err:
            logger.error(f"Network error contacting OpenWeatherMap: {req_err}")
            raise RuntimeError(f"Weather service connection error: {str(req_err)}") from req_err

    # 2. Transparent Mock Mode when OPENWEATHER_API_KEY is not configured
    logger.info("OPENWEATHER_API_KEY not configured. Returning DEMO / MOCK weather payload.")
    return WeatherResult(
        location=clean_location,
        temperature_c=28.5,
        humidity_percent=65,
        rainfall_mm=0.0,
        rainfall_prob_percent=15,
        wind_speed_kmh=12.5,
        forecast="Partly cloudy with mild afternoon breeze",
        agricultural_advisory="Favorable weather for field spraying and harvesting. No heavy rainfall expected in the next 48 hours.",
        source="DEMO / MOCK",
        retrieved_at=datetime.utcnow(),
        is_mock=True
    )

@tool
def weather_tool(location: str = "Mandya, India") -> str:
    """Fetches real-time weather forecast and agricultural spraying advisory."""
    res = get_weather_forecast(location)
    return (
        f"Weather for {res.location}: {res.temperature_c}°C, Humidity: {res.humidity_percent}%, "
        f"Rain: {res.rainfall_mm}mm, Wind: {res.wind_speed_kmh}km/h. Forecast: {res.forecast}. "
        f"Advisory: {res.agricultural_advisory} (Source: {res.source})"
    )
