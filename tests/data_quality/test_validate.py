import pytest

from validate import get_actual_records, resolve_field_path, validate_records


def test_value_mode_uses_total_records():
    validate_records(
        payload={"total_records": 24},
        expected_records=24,
        field_path="total_records",
        validation_mode="value",
    )


def test_count_mode_uses_top_level_list():
    validate_records(
        payload={"records": [{"id": 1}, {"id": 2}]},
        expected_records=2,
        field_path="records",
        validation_mode="count",
    )


def test_count_mode_uses_nested_list():
    validate_records(
        payload={"hourly": {"time": ["00:00", "01:00"]}},
        expected_records=2,
        field_path="hourly.time",
        validation_mode="count",
    )


def test_gte_mode_accepts_list_count_above_expected_minimum():
    validate_records(
        payload={"states": [["flight-1"], ["flight-2"]]},
        expected_records=1,
        field_path="states",
        validation_mode="gte",
    )


def test_gte_mode_accepts_integer_above_expected_minimum():
    validate_records(
        payload={"total_records": 2},
        expected_records=1,
        field_path="total_records",
        validation_mode="gte",
    )


def test_resolve_field_path_returns_nested_value():
    assert resolve_field_path({"hourly": {"time": ["00:00"]}}, "hourly.time") == ["00:00"]


def test_missing_field_exits_with_failure():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"hourly": {}},
            expected_records=2,
            field_path="hourly.time",
            validation_mode="count",
        )

    assert error.value.code == 1


def test_invalid_mode_exits_with_failure():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"total_records": 2},
            expected_records=2,
            field_path="total_records",
            validation_mode="sum",
        )

    assert error.value.code == 1


def test_scalar_count_field_exits_with_failure():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"records": 2},
            expected_records=2,
            field_path="records",
            validation_mode="count",
        )

    assert error.value.code == 1


def test_mismatched_count_exits_with_failure():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"records": [{"id": 1}]},
            expected_records=2,
            field_path="records",
            validation_mode="count",
        )

    assert error.value.code == 1


def test_gte_mode_exits_when_actual_is_below_expected_minimum():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"states": []},
            expected_records=1,
            field_path="states",
            validation_mode="gte",
        )

    assert error.value.code == 1


def test_gte_mode_rejects_scalar_non_integer():
    with pytest.raises(SystemExit) as error:
        validate_records(
            payload={"states": "not-a-list"},
            expected_records=1,
            field_path="states",
            validation_mode="gte",
        )

    assert error.value.code == 1


def test_value_mode_rejects_bool():
    with pytest.raises(ValueError):
        get_actual_records(True, "value")


def test_gte_mode_rejects_bool():
    with pytest.raises(ValueError):
        get_actual_records(True, "gte")
