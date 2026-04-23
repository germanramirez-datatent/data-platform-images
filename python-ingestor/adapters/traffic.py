import os
from datetime import date

import requests

from base_adapter import BaseAdapter


class TrafficAdapter(BaseAdapter):
    source_name = "traffic"
    required_env = ("SIMULATION_API_URL", "CENTER_ID")

    def build_api_url(self) -> str:
        return f"{os.environ['SIMULATION_API_URL'].rstrip('/')}/traffic/range"

    def build_query_params(self, ingest_day: date) -> dict[str, str]:
        date_str = ingest_day.isoformat()
        return {
            "center_id": os.environ["CENTER_ID"],
            "from": date_str,
            "to": date_str,
        }

    def fetch_payload(self, ingest_day: date) -> dict:
        api_url = self.build_api_url()
        params = self.build_query_params(ingest_day)
        self.logger.info("Requesting traffic data from %s with params=%s", api_url, params)

        response = requests.get(
            api_url,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        self.logger.info("Traffic API responded with status_code=%s", response.status_code)
        return response.json()

    def build_object_key(self, ingest_day: date) -> str:
        center_id = os.environ["CENTER_ID"]
        return (
            f"traffic/year={ingest_day.year:04d}/"
            f"month={ingest_day.month:02d}/"
            f"day={ingest_day.day:02d}/"
            f"{center_id}.json"
        )
