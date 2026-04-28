from datetime import datetime

import generator


def test_generator_helpers_apply_expected_factors():
    assert generator.get_hourly_base(12) == 1200
    assert generator.apply_weekday_factor(100, 0) == 70
    assert generator.apply_month_factor(100, 12) == 140
    assert generator.apply_weather_factor(100, "heavy rain", 20) == 70
    assert generator.apply_weather_factor(100, "sunny", 36) == 80


def test_holiday_factor_handles_special_and_regular_holidays():
    assert generator.apply_holiday_factor(100, True, datetime(2026, 1, 1).date()) == 20
    assert generator.apply_holiday_factor(100, True, datetime(2026, 4, 22).date()) == 140
    assert generator.apply_holiday_factor(100, False, datetime(2026, 4, 22).date()) == 100


def test_calculate_visitors_is_deterministic_when_noise_is_patched(monkeypatch):
    monkeypatch.setattr(generator, "apply_noise", lambda base: base)

    visitors = generator.calculate_visitors(
        timestamp=datetime(2026, 4, 22, 12),
        weather_condition="sunny",
        temperature_c=22,
        is_holiday=False,
    )

    assert visitors == int(1200 * 0.8 * 0.85)
