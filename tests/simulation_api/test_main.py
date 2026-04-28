from datetime import date, datetime

import pytest
from fastapi import HTTPException

import main


def test_health_returns_ok():
    assert main.health() == {"status": "ok"}


def test_build_record_uses_defaults_and_timestamp_fields(monkeypatch):
    monkeypatch.setattr(main, "calculate_visitors", lambda **kwargs: 123)

    record = main.build_record(center_id="EUR_MAD_001", timestamp=datetime(2026, 4, 22, 10))

    assert record.center_id == "EUR_MAD_001"
    assert record.visitors_count == 123
    assert record.day_of_week == "wednesday"
    assert record.is_holiday is False
    assert record.weather_condition == "sunny"
    assert record.temperature_c == 22.0


def test_historical_traffic_returns_full_day(monkeypatch):
    monkeypatch.setattr(main, "calculate_visitors", lambda **kwargs: 123)

    response = main.get_historical_traffic(center_id="EUR_MAD_001", date=date(2026, 4, 22))

    assert response.total_records == 24
    assert len(response.records) == 24
    assert response.records[0].timestamp.hour == 0
    assert response.records[-1].timestamp.hour == 23
    assert {record.center_id for record in response.records} == {"EUR_MAD_001"}


def test_traffic_range_returns_records_for_each_day(monkeypatch):
    monkeypatch.setattr(main, "calculate_visitors", lambda **kwargs: 123)

    response = main.get_traffic_range(
        center_id="EUR_MAD_001",
        from_date=date(2026, 4, 22),
        to_date=date(2026, 4, 23),
    )

    assert response.total_records == 48
    assert len(response.records) == 48
    assert response.records[0].timestamp.date() == date(2026, 4, 22)
    assert response.records[-1].timestamp.date() == date(2026, 4, 23)


def test_traffic_range_rejects_invalid_date_range():
    with pytest.raises(HTTPException) as error:
        main.get_traffic_range(
            center_id="EUR_MAD_001",
            from_date=date(2026, 4, 23),
            to_date=date(2026, 4, 22),
        )

    assert error.value.status_code == 400
