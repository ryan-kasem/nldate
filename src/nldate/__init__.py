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

    # 1. Exact named dates
    for name, delta in _NAMED_DATES.items():
        if n == name:
            return today + timedelta(days=delta)

    # 2. Weekday expressions: "next Monday", "last Friday", "this Wed", bare weekday
    r = _try_weekday(n, today)
    if r is not None:
        return r

    # 3. "<N units> ago"
    r = _try_ago(n, today)
    if r is not None:
        return r

    # 4. "in <N units>" or "<N units> from now/today"
    r = _try_simple_future(n, today)
    if r is not None:
        return r

    # 5. "<N units> before/after <anchor>"
    r = _try_offset_anchor(n, today)
    if r is not None:
        return r

    # 6. Calendar landmarks: end/start of month, next/last week/month/year
    r = _try_landmark(n, today)
    if r is not None:
        return r

    # 7. Fall back to dateparser
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

_UNIT_MAP: dict[str, int] = {
    "day": 1,
    "days": 1,
    "week": 7,
    "weeks": 7,
    "month": 30,
    "months": 30,
    "year": 365,
    "years": 365,
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


def _parse_duration(text: str) -> int | None:
    """'3 days', 'two weeks', '1 year and 2 months' -> days. None if no match."""
    total = 0
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
        if n is None or unit not in _UNIT_MAP:
            return None
        total += n * _UNIT_MAP[unit]
        matched = True
    return total if matched else None


def _resolve(anchor: str, today: date) -> date | None:
    """Resolve an anchor phrase to a date."""
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
    days = _parse_duration(m.group(1))
    return today - timedelta(days=days) if days is not None else None


def _try_simple_future(s: str, today: date) -> date | None:
    m = re.match(r"^in\s+(.+)$", s)
    if m:
        days = _parse_duration(m.group(1))
        if days is not None:
            return today + timedelta(days=days)
    m2 = re.match(r"^(.+?)\s+from\s+(?:now|today)$", s)
    if m2:
        days = _parse_duration(m2.group(1))
        if days is not None:
            return today + timedelta(days=days)
    return None


def _try_offset_anchor(s: str, today: date) -> date | None:
    m = re.match(r"^(.+?)\s+(before|after|from|prior to)\s+(.+)$", s)
    if not m:
        return None
    dur_text = re.sub(r"^in\s+", "", m.group(1).strip())
    direction = m.group(2).strip()
    anchor_text = m.group(3).strip()
    days = _parse_duration(dur_text)
    if days is None:
        return None
    anchor = _resolve(anchor_text, today)
    if anchor is None:
        return None
    if direction in ("before", "prior to"):
        return anchor - timedelta(days=days)
    return anchor + timedelta(days=days)


def _try_landmark(s: str, today: date) -> date | None:
    import calendar

    # next/last/this week -> Monday of that week
    if s == "next week":
        return today + timedelta(days=7 - today.weekday())
    if s in ("last week", "previous week"):
        return today - timedelta(days=today.weekday() + 7)

    # next/last/this month -> same day
    if s == "next month":
        m, y = (today.month % 12) + 1, today.year + (today.month // 12)
        return date(y, m, min(today.day, calendar.monthrange(y, m)[1]))
    if s in ("last month", "previous month"):
        m = today.month - 1 or 12
        y = today.year - (1 if today.month == 1 else 0)
        return date(y, m, min(today.day, calendar.monthrange(y, m)[1]))

    # next/last year
    if s == "next year":
        return date(today.year + 1, today.month, today.day)
    if s in ("last year", "previous year"):
        return date(today.year - 1, today.month, today.day)

    # end/start of month (current or next/last)
    if "next month" in s:
        m2 = (today.month % 12) + 1
        y2 = today.year + (today.month // 12)
    elif "last month" in s or "previous month" in s:
        m2 = today.month - 1 or 12
        y2 = today.year - (1 if today.month == 1 else 0)
    else:
        m2, y2 = today.month, today.year

    last = calendar.monthrange(y2, m2)[1]
    if re.search(r"\bend of\b|\blast day of\b", s):
        return date(y2, m2, last)
    if re.search(r"\b(beginning of|start of|first day of)\b", s):
        return date(y2, m2, 1)

    return None
