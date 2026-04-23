import os
from datetime import date

import requests

from base_adapter import BaseAdapter


class HolidaysAdapter(BaseAdapter):
    source_name = "holidays"
    required_env = ("HOLIDAYS_COUNTRY_CODE",)

    def fetch_payload(self, ingest_day: date) -> dict:
        country_code = os.environ["HOLIDAYS_COUNTRY_CODE"]
        base_url = os.environ.get("NAGER_DATE_URL", "https://date.nager.at/api/v3/PublicHolidays")
        api_url = f"{base_url}/{ingest_day.year}/{country_code}"
        self.logger.info("Requesting holiday data from %s", api_url)

        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        holidays = response.json()
        matching_holidays = [holiday for holiday in holidays if holiday.get("date") == ingest_day.isoformat()]
        return {
            "source": self.source_name,
            "country_code": country_code,
            "ingest_date": ingest_day.isoformat(),
            "total_records": len(matching_holidays),
            "holidays": matching_holidays,
        }

    def build_object_key(self, ingest_day: date) -> str:
        country_code = os.environ["HOLIDAYS_COUNTRY_CODE"]
        return (
            f"holidays/year={ingest_day.year:04d}/"
            f"month={ingest_day.month:02d}/"
            f"day={ingest_day.day:02d}/"
            f"{country_code}.json"
        )
