from datetime import date

import pytest

from adapters import get_adapter
from adapters.flights import FlightsAdapter
from adapters.holidays import HolidaysAdapter
from adapters.traffic import TrafficAdapter
from adapters.weather import WeatherAdapter


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


def test_get_adapter_normalizes_source_name(monkeypatch):
    monkeypatch.setenv("WEATHER_LATITUDE", "40.4168")
    monkeypatch.setenv("WEATHER_LONGITUDE", "-3.7038")

    adapter = get_adapter(" WEATHER ")

    assert isinstance(adapter, WeatherAdapter)


def test_get_adapter_rejects_unsupported_source():
    with pytest.raises(ValueError, match="Unsupported INGEST_SOURCE"):
        get_adapter("unknown")


def test_traffic_adapter_builds_url_params_and_object_key(monkeypatch):
    monkeypatch.setenv("SIMULATION_API_URL", "http://simulation-api:8000/")
    monkeypatch.setenv("CENTER_ID", "EUR_MAD_001")
    adapter = TrafficAdapter()
    ingest_day = date(2026, 4, 22)

    assert adapter.build_api_url() == "http://simulation-api:8000/traffic/range"
    assert adapter.build_query_params(ingest_day) == {
        "center_id": "EUR_MAD_001",
        "from": "2026-04-22",
        "to": "2026-04-22",
    }
    assert adapter.build_object_key(ingest_day) == "traffic/year=2026/month=04/day=22/EUR_MAD_001.json"


def test_traffic_adapter_fetches_payload(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse({"records": [{"hour": 1}], "total_records": 1})

    monkeypatch.setenv("SIMULATION_API_URL", "http://simulation-api:8000")
    monkeypatch.setenv("CENTER_ID", "EUR_MAD_001")
    monkeypatch.setattr("adapters.traffic.requests.get", fake_get)

    payload = TrafficAdapter().fetch_payload(date(2026, 4, 22))

    assert payload == {"records": [{"hour": 1}], "total_records": 1}
    assert calls[0]["url"] == "http://simulation-api:8000/traffic/range"
    assert calls[0]["params"]["center_id"] == "EUR_MAD_001"
    assert calls[0]["timeout"] == 30


def test_weather_adapter_shapes_payload_and_object_key(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse({"hourly": {"time": ["00:00", "01:00"]}})

    monkeypatch.setenv("WEATHER_LATITUDE", "40.4168")
    monkeypatch.setenv("WEATHER_LONGITUDE", "-3.7038")
    monkeypatch.setenv("WEATHER_TIMEZONE", "Europe/Madrid")
    monkeypatch.setenv("OPEN_METEO_URL", "http://weather.example/archive")
    monkeypatch.setattr("adapters.weather.requests.get", fake_get)
    adapter = WeatherAdapter()
    ingest_day = date(2026, 4, 22)

    payload = adapter.fetch_payload(ingest_day)

    assert payload["source"] == "weather"
    assert payload["ingest_date"] == "2026-04-22"
    assert payload["total_records"] == 2
    assert adapter.build_object_key(ingest_day) == "weather/year=2026/month=04/day=22/open-meteo.json"
    assert calls[0]["params"]["timezone"] == "Europe/Madrid"


def test_holidays_adapter_filters_matching_day_and_object_key(monkeypatch):
    def fake_get(url, timeout):
        assert url == "http://holidays.example/2026/ES"
        assert timeout == 30
        return FakeResponse(
            [
                {"date": "2026-04-22", "name": "Matching holiday"},
                {"date": "2026-04-23", "name": "Other holiday"},
            ]
        )

    monkeypatch.setenv("HOLIDAYS_COUNTRY_CODE", "ES")
    monkeypatch.setenv("NAGER_DATE_URL", "http://holidays.example")
    monkeypatch.setattr("adapters.holidays.requests.get", fake_get)
    adapter = HolidaysAdapter()
    ingest_day = date(2026, 4, 22)

    payload = adapter.fetch_payload(ingest_day)

    assert payload["source"] == "holidays"
    assert payload["country_code"] == "ES"
    assert payload["total_records"] == 1
    assert payload["holidays"] == [{"date": "2026-04-22", "name": "Matching holiday"}]
    assert adapter.build_object_key(ingest_day) == "holidays/year=2026/month=04/day=22/ES.json"


def test_flights_adapter_fetches_token_shapes_payload_and_object_key(monkeypatch):
    post_calls = []
    get_calls = []

    def fake_post(url, data, headers, timeout):
        post_calls.append({"url": url, "data": data, "headers": headers, "timeout": timeout})
        return FakeResponse({"access_token": "token-123"})

    def fake_get(url, params, headers, timeout):
        get_calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return FakeResponse({"states": [["flight-1"], ["flight-2"]]})

    monkeypatch.setenv("OPENSKY_CLIENT_ID", "client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OPENSKY_LAMIN", "39.8")
    monkeypatch.setenv("OPENSKY_LAMAX", "41.0")
    monkeypatch.setenv("OPENSKY_LOMIN", "-4.0")
    monkeypatch.setenv("OPENSKY_LOMAX", "-3.0")
    monkeypatch.setenv("OPENSKY_AREA_NAME", "madrid")
    monkeypatch.setenv("OPENSKY_TOKEN_URL", "http://opensky.example/token")
    monkeypatch.setenv("OPENSKY_URL", "http://opensky.example/states")
    monkeypatch.setattr("adapters.flights.requests.post", fake_post)
    monkeypatch.setattr("adapters.flights.requests.get", fake_get)
    adapter = FlightsAdapter()
    monkeypatch.setattr(adapter, "build_snapshot_time", lambda ingest_day: 1234567890)
    ingest_day = date(2026, 4, 22)

    payload = adapter.fetch_payload(ingest_day)

    assert payload["source"] == "flights"
    assert payload["ingest_date"] == "2026-04-22"
    assert payload["snapshot_time"] == 1234567890
    assert payload["total_records"] == 2
    assert post_calls[0]["data"]["client_id"] == "client"
    assert get_calls[0]["headers"] == {"Authorization": "Bearer token-123"}
    assert get_calls[0]["params"]["time"] == 1234567890
    assert adapter.build_object_key(ingest_day) == "flights/year=2026/month=04/day=22/madrid.json"


def test_flights_adapter_rejects_token_response_without_access_token(monkeypatch):
    def fake_post(url, data, headers, timeout):
        return FakeResponse({})

    monkeypatch.setenv("OPENSKY_CLIENT_ID", "client")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OPENSKY_LAMIN", "39.8")
    monkeypatch.setenv("OPENSKY_LAMAX", "41.0")
    monkeypatch.setenv("OPENSKY_LOMIN", "-4.0")
    monkeypatch.setenv("OPENSKY_LOMAX", "-3.0")
    monkeypatch.setattr("adapters.flights.requests.post", fake_post)

    with pytest.raises(ValueError, match="access_token"):
        FlightsAdapter().get_access_token()
