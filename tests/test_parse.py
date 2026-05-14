"""Tests for nldate.parse()."""

from datetime import date, timedelta

import pytest

from nldate import parse

# Use a fixed reference date so tests are deterministic
TODAY = date(2025, 6, 15)  # Sunday


# ---------------------------------------------------------------------------
# Fixed / absolute dates
# ---------------------------------------------------------------------------


def test_iso_date() -> None:
    assert parse("2025-12-25", today=TODAY) == date(2025, 12, 25)


def test_full_written_date() -> None:
    assert parse("December 1st, 2025", today=TODAY) == date(2025, 12, 1)


def test_short_written_date() -> None:
    assert parse("Jan 3, 2024", today=TODAY) == date(2024, 1, 3)


def test_slash_date() -> None:
    assert parse("07/04/2026", today=TODAY) == date(2026, 7, 4)


def test_month_year_only() -> None:
    result = parse("March 2026", today=TODAY)
    assert result.year == 2026
    assert result.month == 3


# ---------------------------------------------------------------------------
# Named relative dates
# ---------------------------------------------------------------------------


def test_today() -> None:
    assert parse("today", today=TODAY) == TODAY


def test_tomorrow() -> None:
    assert parse("tomorrow", today=TODAY) == TODAY + timedelta(days=1)


def test_yesterday() -> None:
    assert parse("yesterday", today=TODAY) == TODAY - timedelta(days=1)


def test_day_after_tomorrow() -> None:
    assert parse("the day after tomorrow", today=TODAY) == TODAY + timedelta(days=2)


def test_day_before_yesterday() -> None:
    assert parse("the day before yesterday", today=TODAY) == TODAY - timedelta(days=2)


# ---------------------------------------------------------------------------
# Weekday expressions
# ---------------------------------------------------------------------------


def test_next_monday() -> None:
    # TODAY is Sunday (wd=6); next Monday is +1
    assert parse("next Monday", today=TODAY) == date(2025, 6, 16)


def test_next_friday() -> None:
    # next Friday from Sunday = +5
    assert parse("next Friday", today=TODAY) == date(2025, 6, 20)


def test_last_friday() -> None:
    # last Friday from Sunday (wd=6) -> Friday (wd=4) = -2
    assert parse("last Friday", today=TODAY) == date(2025, 6, 13)


def test_next_tuesday() -> None:
    # Sunday -> next Tuesday = +2
    assert parse("next Tuesday", today=TODAY) == date(2025, 6, 17)


# ---------------------------------------------------------------------------
# Relative durations ("in N units", "N units from now")
# ---------------------------------------------------------------------------


def test_in_3_days() -> None:
    assert parse("in 3 days", today=TODAY) == TODAY + timedelta(days=3)


def test_in_two_weeks() -> None:
    assert parse("in two weeks", today=TODAY) == TODAY + timedelta(weeks=2)


def test_in_a_month() -> None:
    assert parse("in a month", today=TODAY) == TODAY + timedelta(days=30)


def test_in_one_year() -> None:
    assert parse("in one year", today=TODAY) == TODAY + timedelta(days=365)


def test_three_weeks_from_now() -> None:
    assert parse("three weeks from now", today=TODAY) == TODAY + timedelta(weeks=3)


def test_5_days_from_today() -> None:
    assert parse("5 days from today", today=TODAY) == TODAY + timedelta(days=5)


# ---------------------------------------------------------------------------
# Offset before/after an anchor
# ---------------------------------------------------------------------------


def test_5_days_before_fixed_date() -> None:
    assert parse("5 days before December 1st, 2025", today=TODAY) == date(2025, 11, 26)


def test_1_week_after_tomorrow() -> None:
    tomorrow = TODAY + timedelta(days=1)
    assert parse("1 week after tomorrow", today=TODAY) == tomorrow + timedelta(weeks=1)


def test_3_days_before_yesterday() -> None:
    yesterday = TODAY - timedelta(days=1)
    assert parse("3 days before yesterday", today=TODAY) == yesterday - timedelta(days=3)


def test_2_weeks_after_today() -> None:
    assert parse("2 weeks after today", today=TODAY) == TODAY + timedelta(weeks=2)


def test_compound_duration() -> None:
    # 1 year and 2 months = 365 + 60 = 425 days
    assert parse("1 year and 2 months after today", today=TODAY) == TODAY + timedelta(days=425)


def test_compound_before_fixed_date() -> None:
    # 1 week and 2 days = 9 days before Dec 1 2025
    assert parse("1 week and 2 days before December 1st, 2025", today=TODAY) == date(2025, 11, 22)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_default_today_used_when_not_provided() -> None:
    """When today is None, result should equal parsing with date.today()."""
    result = parse("tomorrow")
    expected = date.today() + timedelta(days=1)
    assert result == expected


def test_invalid_raises_value_error() -> None:
    with pytest.raises(ValueError):
        parse("not a date at all xyzzy", today=TODAY)
