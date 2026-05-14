"""nldate: Natural-language date parser."""

from __future__ import annotations

import re
from datetime import date, timedelta

import dateparser


def parse(s: str, today: date | None = None) -> date:
    """Parse a natural-language date string into a datetime.date.

    Args:
        s: Natural language date string, e.g. "5 days before December 1st, 2025",
           "next Tuesday", "in 3 weeks", "1 year and 2 months after yesterday".
        today: Reference date for relative expressions. Defaults to today.

    Returns:
        A datetime.date representing the parsed date.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    if today is None:
        today = date.today()

    n = s.strip().lower()

    for name, delta in _NAMED_DATES.items():
        if n == name:
            return today + timedelta(days=delta)

    r = _try_weekday(n, today)
    if r is not None:
        return r

    r = _try_ago(n, today)
    if r is not None:
        return r

    r = _try_simple_future(n, today)
    if r is not None:
        return r

    r = _try_offset_anchor(n, today)
    if r is not None:
        return r

    r = _try_landmark(n, today)
    if r is not None:
        return r

    settings: dict[str, object] = {
        "RELATIVE_BASE": _to_dt(today),
        "PREFER_DAY_OF_MONTH": "first",
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed = dateparser.parse(s, settings=settings)
    if parsed is not None:
        return parsed.date()

    raise ValueError(f"Could not parse date string: {s!r}")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NAMED_DATES: dict[str, int] = {
    "today": 0,
    "tomorrow": 1,
    "yesterday": -1,
    "the day after tomorrow": 2,
    "the day before yesterday": -2,
}

_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

# days only (weeks count as days)
_DAY_UNITS: dict[str, int] = {
    "day": 1,
    "days": 1,
    "week": 7,
    "weeks": 7,
}

# months (years = 12 months)
_MONTH_UNITS: dict[str, int] = {
    "month": 1,
    "months": 1,
    "year": 12,
    "years": 12,
}

_WORDS: dict[str, int] = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_dt(d: date) -> object:
    from datetime import datetime

    return datetime(d.year, d.month, d.day)


def _num(tok: str) -> int | None:
    tok = tok.strip()
    if tok.isdigit():
        return int(tok)
    return _WORDS.get(tok)


# Duration is (days, months) where months includes years*12
def _parse_duration(text: str) -> tuple[int, int] | None:
    """Parse a duration string into (extra_days, total_months)."""
    total_days = 0
    total_months = 0
    matched = False
    for part in re.split(r"\band\b|,", text):
        part = part.strip()
        m = re.match(r"^(\w+)\s+(days?|weeks?|months?|years?)$", part)
        if not m:
            return None
        n = _num(m.group(1))
        unit = m.group(2)
        if not unit.endswith("s"):
            unit += "s"
        if n is None:
            return None
        if unit in _DAY_UNITS:
            total_days += n * _DAY_UNITS[unit]
        elif unit in _MONTH_UNITS:
            total_months += n * _MONTH_UNITS[unit]
        else:
            return None
        matched = True
    return (total_days, total_months) if matched else None


def _shift_months(d: date, months: int) -> date:
    """Add (or subtract if negative) an exact number of months."""
    import calendar

    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_dur(d: date, days: int, months: int) -> date:
    if months:
        d = _shift_months(d, months)
    return d + timedelta(days=days)


def _sub_dur(d: date, days: int, months: int) -> date:
    if months:
        d = _shift_months(d, -months)
    return d - timedelta(days=days)


def _try_weekday(s: str, today: date) -> date | None:
    m = re.match(r"^(next|last|this)?\s*(\w+)$", s)
    if not m:
        return None
    qual, day = m.group(1) or "", m.group(2)
    if day not in _WEEKDAYS:
        return None
    target = _WEEKDAYS[day]
    cur = today.weekday()
    if qual == "last":
        delta = -((cur - target) % 7) or -7
    else:
        delta = (target - cur) % 7 or 7
    return today + timedelta(days=delta)


def _try_ago(s: str, today: date) -> date | None:
    m = re.match(r"^(.+?)\s+ago$", s)
    if not m:
        return None
    dur = _parse_duration(m.group(1))
    return _sub_dur(today, dur[0], dur[1]) if dur is not None else None


def _try_simple_future(s: str, today: date) -> date | None:
    m = re.match(r"^in\s+(.+)$", s)
    if m:
        dur = _parse_duration(m.group(1))
        if dur is not None:
            return _add_dur(today, dur[0], dur[1])
    m2 = re.match(r"^(.+?)\s+from\s+(?:now|today)$", s)
    if m2:
        dur = _parse_duration(m2.group(1))
        if dur is not None:
            return _add_dur(today, dur[0], dur[1])
    return None


def _resolve(anchor: str, today: date) -> date | None:
    for name, delta in _NAMED_DATES.items():
        if anchor == name:
            return today + timedelta(days=delta)
    r = _try_weekday(anchor, today)
    if r is not None:
        return r
    from datetime import datetime

    settings: dict[str, object] = {
        "RELATIVE_BASE": _to_dt(today),
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed: datetime | None = dateparser.parse(anchor, settings=settings)
    return parsed.date() if parsed else None


def _try_offset_anchor(s: str, today: date) -> date | None:
    m = re.match(r"^(.+?)\s+(before|after|from|prior to)\s+(.+)$", s)
    if not m:
        return None
    dur_text = re.sub(r"^in\s+", "", m.group(1).strip())
    direction = m.group(2).strip()
    anchor_text = m.group(3).strip()
    dur = _parse_duration(dur_text)
    if dur is None:
        return None
    anchor = _resolve(anchor_text, today)
    if anchor is None:
        return None
    if direction in ("before", "prior to"):
        return _sub_dur(anchor, dur[0], dur[1])
    return _add_dur(anchor, dur[0], dur[1])


def _try_landmark(s: str, today: date) -> date | None:
    import calendar

    if s == "next week":
        return today + timedelta(days=7 - today.weekday())
    if s in ("last week", "previous week"):
        return today - timedelta(days=today.weekday() + 7)

    if s == "next month":
        return _shift_months(today, 1)
    if s in ("last month", "previous month"):
        return _shift_months(today, -1)

    if s == "next year":
        return _shift_months(today, 12)
    if s in ("last year", "previous year"):
        return _shift_months(today, -12)

    if "next month" in s:
        y2, m2 = (_shift_months(today, 1).year, _shift_months(today, 1).month)
    elif "last month" in s or "previous month" in s:
        y2, m2 = (_shift_months(today, -1).year, _shift_months(today, -1).month)
    elif "next year" in s:
        y2, m2 = today.year + 1, today.month
    else:
        y2, m2 = today.year, today.month

    last = calendar.monthrange(y2, m2)[1]
    if re.search(r"\bend of\b|\blast day of\b", s):
        return date(y2, m2, last)
    if re.search(r"\b(beginning of|start of|first day of)\b", s):
        return date(y2, m2, 1)

    return None
