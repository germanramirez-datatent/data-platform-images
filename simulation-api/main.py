from fastapi import FastAPI, HTTPException, Query
from datetime import date, datetime, timedelta

from models import TrafficRecord, TrafficResponse
from generator import calculate_visitors

app = FastAPI()

DEFAULT_WEATHER = "sunny"
DEFAULT_TEMPERATURE_C = 22.0
DEFAULT_IS_HOLIDAY = False


def build_record(center_id: str, timestamp: datetime) -> TrafficRecord:
    visitors_count = calculate_visitors(
        timestamp=timestamp,
        weather_condition=DEFAULT_WEATHER,
        temperature_c=DEFAULT_TEMPERATURE_C,
        is_holiday=DEFAULT_IS_HOLIDAY,
    )

    return TrafficRecord(
        center_id=center_id,
        timestamp=timestamp,
        visitors_count=visitors_count,
        day_of_week=timestamp.strftime("%A").lower(),
        is_holiday=DEFAULT_IS_HOLIDAY,
        weather_condition=DEFAULT_WEATHER,
        temperature_c=DEFAULT_TEMPERATURE_C,
    )


@app.get("/health")
def health():
    # returns health status
    return {"status": "ok"}


@app.get("/traffic/current", response_model=TrafficRecord)
def get_current_traffic(center_id: str):
    # returns current traffic for the given center
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    return build_record(center_id=center_id, timestamp=now)


@app.get("/traffic/historical", response_model=TrafficResponse)
def get_historical_traffic(center_id: str, date: date):
    # returns hourly traffic for a full day (24 records)
    records = [
        build_record(
            center_id=center_id,
            timestamp=datetime.combine(date, datetime.min.time()).replace(hour=hour),
        )
        for hour in range(24)
    ]
    return TrafficResponse(records=records, total_records=len(records))


@app.get("/traffic/range", response_model=TrafficResponse)
def get_traffic_range(
    center_id: str,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
):
    # returns hourly traffic for a date range
    if from_date > to_date:
        raise HTTPException(status_code=400, detail="'from' date must be before or equal to 'to' date")

    records = []
    current_date = from_date
    while current_date <= to_date:
        records.extend(
            build_record(
                center_id=center_id,
                timestamp=datetime.combine(current_date, datetime.min.time()).replace(hour=hour),
            )
            for hour in range(24)
        )
        current_date += timedelta(days=1)

    return TrafficResponse(records=records, total_records=len(records))
