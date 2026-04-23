import os
from datetime import date, datetime, time, timezone

import requests

from base_adapter import BaseAdapter


class FlightsAdapter(BaseAdapter):
    source_name = "flights"
    required_env = (
        "OPENSKY_CLIENT_ID",
        "OPENSKY_CLIENT_SECRET",
        "OPENSKY_LAMIN",
        "OPENSKY_LAMAX",
        "OPENSKY_LOMIN",
        "OPENSKY_LOMAX",
    )

    def get_access_token(self) -> str:
        token_url = os.environ.get(
            "OPENSKY_TOKEN_URL",
            "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token",
        )
        token_payload = {
            "grant_type": "client_credentials",
            "client_id": os.environ["OPENSKY_CLIENT_ID"],
            "client_secret": os.environ["OPENSKY_CLIENT_SECRET"],
        }
        self.logger.info("Requesting OpenSky OAuth2 token from %s", token_url)

        response = requests.post(
            token_url,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )
        response.raise_for_status()
        token_response = response.json()

        access_token = token_response.get("access_token")
        if not access_token:
            raise ValueError("OpenSky token response did not include access_token")

        return access_token

    def build_snapshot_time(self, ingest_day: date) -> int:
        now_utc = datetime.now(timezone.utc)
        requested_day = datetime.combine(ingest_day, time.min, tzinfo=timezone.utc).date()
        requested_snapshot = datetime.combine(requested_day, now_utc.time(), tzinfo=timezone.utc)

        # OpenSky /states/all only supports snapshots up to about 1 hour in the past for authenticated users.
        if requested_day != now_utc.date():
            self.logger.info(
                "Requested ingest_date=%s is outside near-real-time mode; using current UTC date %s instead",
                ingest_day.isoformat(),
                now_utc.date().isoformat(),
            )
            requested_snapshot = now_utc

        one_hour_ago = now_utc.timestamp() - 3600
        snapshot_timestamp = int(requested_snapshot.timestamp())
        if snapshot_timestamp < one_hour_ago:
            self.logger.info(
                "Requested flight snapshot is older than one hour; using current UTC timestamp instead",
            )
            snapshot_timestamp = int(now_utc.timestamp())

        return snapshot_timestamp

    def fetch_payload(self, ingest_day: date) -> dict:
        api_url = os.environ.get("OPENSKY_URL", "https://opensky-network.org/api/states/all")
        snapshot_timestamp = self.build_snapshot_time(ingest_day)
        params = {
            "time": snapshot_timestamp,
            "lamin": os.environ["OPENSKY_LAMIN"],
            "lamax": os.environ["OPENSKY_LAMAX"],
            "lomin": os.environ["OPENSKY_LOMIN"],
            "lomax": os.environ["OPENSKY_LOMAX"],
        }
        access_token = self.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}

        self.logger.info("Requesting flight data from %s with params=%s", api_url, params)
        response = requests.get(api_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        payload["source"] = self.source_name
        payload["ingest_date"] = ingest_day.isoformat()
        payload["snapshot_time"] = snapshot_timestamp
        return payload

    def build_object_key(self, ingest_day: date) -> str:
        area_label = os.environ.get("OPENSKY_AREA_NAME", "Madrid")
        return (
            f"flights/year={ingest_day.year:04d}/"
            f"month={ingest_day.month:02d}/"
            f"day={ingest_day.day:02d}/"
            f"{area_label}.json"
        )
