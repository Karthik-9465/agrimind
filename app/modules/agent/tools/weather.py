import os
import requests
import logging
from typing import Optional
from langchain_core.tools import tool
from app.modules.agent.schemas import WeatherResult

logger = logging.getLogger("agrimind.weather")

def get_weather_forecast(location: str = "Mandya, India") -> WeatherResult:
    """
    Fetches real-time weather forecast via OpenWeatherMap API if OPENWEATHER_API_KEY is configured.
    Falls back to explicit DEMO / MOCK mode when key is absent.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    clean_location = location.strip() if location else "Mandya, India"

    # 1. Missing API Key -> Explicit Mock Mode
    if not api_key:
        logger.info("OPENWEATHER_API_KEY not found in environment. Returning DEMO / MOCK weather payload.")
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
            is_mock=True
        )

    # 2. Valid API Key -> Call OpenWeatherMap API
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": clean_location,
            "units": "metric",
            "appid": api_key
        }
        res = requests.get(url, params=params, timeout=6)
        
        if res.status_code != 200:
            logger.error(f"OpenWeatherMap API error status {res.status_code}: {res.text}")
            raise RuntimeError(f"Weather service returned HTTP error status {res.status_code}.")

        data = res.json()
        temp = data.get("main", {}).get("temp", 25.0)
        humidity = data.get("main", {}).get("humidity", 60)
        wind_speed_ms = data.get("wind", {}).get("speed", 3.0)
        wind_kmh = round(wind_speed_ms * 3.6, 1)
        rain_mm = data.get("rain", {}).get("1h", 0.0)
        weather_desc = data.get("weather", [{}])[0].get("description", "Clear sky").capitalize()

        # Generate advisory based on real weather
        if rain_mm > 5.0 or humidity > 85:
            advisory = f"High humidity ({humidity}%) and rain ({rain_mm} mm) observed. Postpone foliar spraying to prevent chemical wash-off."
        elif temp > 35:
            advisory = f"High temperature ({temp}°C) recorded. Ensure adequate evening irrigation to avoid heat stress."
        else:
            advisory = f"Optimal weather conditions for field operations and routine crop monitoring."

        return WeatherResult(
            location=data.get("name", clean_location),
            temperature_c=temp,
            humidity_percent=humidity,
            rainfall_mm=rain_mm,
            rainfall_prob_percent=80 if rain_mm > 0 else 20,
            wind_speed_kmh=wind_kmh,
            forecast=weather_desc,
            agricultural_advisory=advisory,
            source="OpenWeatherMap",
            is_mock=False
        )

    except requests.RequestException as req_err:
        logger.error(f"Network error contacting OpenWeatherMap API: {str(req_err)}")
        raise RuntimeError("Weather service connection timeout or network failure.") from req_err
    except Exception as e:
        logger.error(f"Weather lookup error: {str(e)}")
        raise RuntimeError(f"Weather service error: {str(e)}") from e

@tool
def weather_tool(location: str = "Mandya, India") -> str:
    """Fetches real-time weather forecast and agricultural spraying advisory."""
    res = get_weather_forecast(location)
    return f"Weather for {res.location}: {res.temperature_c}°C, Humidity: {res.humidity_percent}%, Forecast: {res.forecast}. Advisory: {res.agricultural_advisory} (Source: {res.source})"
