from pydantic import BaseModel
from datetime import datetime

class TrafficRecord(BaseModel):
    center_id: str
    timestamp: datetime
    visitors_count: int
    day_of_week: str
    is_holiday: bool
    weather_condition: str
    temperature_c: float

class TrafficResponse(BaseModel):
    records: list[TrafficRecord]
    total_records: int