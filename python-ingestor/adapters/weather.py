import os
from datetime import date

import requests

from base_adapter import BaseAdapter


class WeatherAdapter(BaseAdapter):
    source_name = "weather"
    required_env = ("WEATHER_LATITUDE", "WEATHER_LONGITUDE")

    def fetch_payload(self, ingest_day: date) -> dict:
        api_url = os.environ.get("OPEN_METEO_URL", "https://archive-api.open-meteo.com/v1/archive")
        params = {
            "latitude": os.environ["WEATHER_LATITUDE"],
            "longitude": os.environ["WEATHER_LONGITUDE"],
            "start_date": ingest_day.isoformat(),
            "end_date": ingest_day.isoformat(),
            "hourly": "temperature_2m,precipitation,windspeed_10m,weathercode",
            "timezone": os.environ.get("WEATHER_TIMEZONE", "Europe/Madrid "),
        }
        self.logger.info("Requesting weather data from %s with params=%s", api_url, params)

        response = requests.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        payload["source"] = self.source_name
        payload["ingest_date"] = ingest_day.isoformat()
        payload["total_records"] = len(payload.get("hourly", {}).get("time", []))
        return payload

    def build_object_key(self, ingest_day: date) -> str:
        return (
            f"weather/year={ingest_day.year:04d}/"
            f"month={ingest_day.month:02d}/"
            f"day={ingest_day.day:02d}/"
            "open-meteo.json"
        )
