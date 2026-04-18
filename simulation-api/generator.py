import random
from datetime import date, datetime
from typing import Optional

HOURLY_BASE = {
    0: 50,   1: 30,   2: 20,   3: 15,   4: 15,
    5: 20,   6: 50,   7: 150,  8: 400,  9: 700,
    10: 900, 11: 1100, 12: 1200, 13: 1100, 14: 950,
    15: 850, 16: 900, 17: 1100, 18: 1200, 19: 1000,
    20: 700, 21: 400, 22: 150, 23: 80
}

WEEKDAY_MULTIPLIER = {
    0: 0.7,  # monday
    1: 0.75, # tuesday
    2: 0.8,  # wednesday
    3: 0.85, # thursday
    4: 1.1,  # friday
    5: 1.5,  # saturday
    6: 1.3   # sunday
}

MONTH_MULTIPLIER = {
    1: 0.6,  2: 0.65, 3: 0.8,
    4: 0.85, 5: 0.9,  6: 0.85,
    7: 0.7,  8: 0.65, 9: 0.85,
    10: 0.9, 11: 1.1, 12: 1.4
}


def get_hourly_base(hour: int) -> int:
    # returns base traffic for the given hour
    return HOURLY_BASE[hour]


def apply_weekday_factor(base: float, weekday: int) -> float:
    # applies weekday multiplier to base traffic
    return base * WEEKDAY_MULTIPLIER[weekday]


def apply_month_factor(base: float, month: int) -> float:
    # applies monthly seasonality multiplier
    return base * MONTH_MULTIPLIER[month]


def apply_weather_factor(base: float, weather: str, temperature: float) -> float:
    # heavy rain: -30%
    # extreme heat >35C: -20%
    # otherwise: no change
    if weather == 'heavy rain':
        base = base - (base * 0.3)
    elif temperature > 35:
        base = base - (base * 0.2)
    return base


def apply_holiday_factor(base: float, is_holiday: bool, dt: date) -> float:
    # regular holiday: +40%
    # dec 25 and jan 1: -80%
    if (dt.month == 12 and dt.day == 25) or (dt.month == 1 and dt.day == 1):
        base = base * 0.2
    elif is_holiday:
        base = base * 1.4
    return base


def apply_noise(base: float) -> float:
    # random noise +/- 15%
    noise_range = base * 0.15
    min_value = base - noise_range
    max_value = base + noise_range

    return random.uniform(min_value, max_value)


def calculate_visitors(
    timestamp: datetime,
    weather_condition: str,
    temperature_c: float,
    is_holiday: bool
) -> int:
    base = get_hourly_base(timestamp.hour)
    base = apply_weekday_factor(base, timestamp.weekday())
    base = apply_month_factor(base, timestamp.month)
    base = apply_weather_factor(base, weather_condition, temperature_c)
    base = apply_holiday_factor(base, is_holiday, timestamp.date())
    base = apply_noise(base)
    return int(base)