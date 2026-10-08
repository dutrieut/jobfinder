import sys
from datetime import datetime, timedelta, timezone

import pytest

from jobfinder.adapters import parse_date


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def test_none_returns_none():
    assert parse_date(None) is None


def test_unix_milliseconds_lever():
    assert parse_date(1790154788619) == utc(2026, 9, 23, 9, 13, 8, 619000)


def test_unix_epoch_zero():
    assert parse_date(0) == utc(1970, 1, 1)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-08-14T15:17:23.480+00:00", utc(2026, 8, 14, 15, 17, 23, 480000)),
        ("2026-09-02T05:38:47-04:00", utc(2026, 9, 2, 9, 38, 47)),
        ("2026-09-02T11:38:47+02:00", utc(2026, 9, 2, 9, 38, 47)),
        ("2026-09-02T23:30:00-04:00", utc(2026, 9, 3, 3, 30)),
    ],
)
def test_iso_strings_are_converted_to_utc(value, expected):
    assert parse_date(value) == expected


def test_iso_with_z_suffix():
    assert parse_date("2026-08-14T15:17:23Z") == utc(2026, 8, 14, 15, 17, 23)


@pytest.mark.parametrize(
    "value",
    [1790154788619, "2026-09-02T05:38:47-04:00", "2026-08-14T15:17:23+00:00"],
)
def test_result_is_always_utc_aware(value):
    result = parse_date(value)
    assert result is not None
    assert result.utcoffset() == timedelta(0)


def test_same_instant_in_different_formats_is_equal():
    assert parse_date("2026-09-02T05:38:47-04:00") == parse_date(
        "2026-09-02T11:38:47+02:00"
    )


@pytest.mark.parametrize("value", ["", "not a date", "2026-13-45"])
def test_invalid_string_raises(value):
    with pytest.raises(ValueError):
        parse_date(value)
