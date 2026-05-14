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

    normalized = s.strip().lower()

    # Try custom relative-offset patterns first ("X before/after Y")
    result = _parse_relative_offset(normalized, today)
    if result is not None:
        return result

    # Handle weekday expressions directly (dateparser ignores RELATIVE_BASE for these)
    result = _parse_weekday_expression(normalized, today)
    if result is not None:
        return result

    # Handle named relative dates
    for name, delta in _NAMED_DATES.items():
        if normalized == name:
            return today + timedelta(days=delta)

    # Delegate to dateparser for everything else
    settings: dict[str, object] = {
        "RELATIVE_BASE": _date_to_datetime(today),
        "PREFER_DAY_OF_MONTH": "first",
        "PREFER_DATES_FROM": "future",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed = dateparser.parse(s, settings=settings)
    if parsed is not None:
        return parsed.date()

    raise ValueError(f"Could not parse date string: {s!r}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_UNIT_DAYS: dict[str, int] = {
    "day": 1,
    "days": 1,
    "week": 7,
    "weeks": 7,
    "month": 30,
    "months": 30,
    "year": 365,
    "years": 365,
}

_WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

_WORD_NUMBERS: dict[str, int] = {
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
    "twenty": 20,
    "thirty": 30,
    "a": 1,
    "an": 1,
}

_NAMED_DATES = {
    "today": 0,
    "tomorrow": 1,
    "yesterday": -1,
    "the day after tomorrow": 2,
    "the day before yesterday": -2,
}


def _date_to_datetime(d: date) -> object:
    """Convert date to datetime for dateparser settings."""
    from datetime import datetime

    return datetime(d.year, d.month, d.day)


def _parse_number(token: str) -> int | None:
    """Parse a word or digit token into an integer."""
    token = token.strip()
    if token.isdigit():
        return int(token)
    return _WORD_NUMBERS.get(token)


def _parse_compound_duration(text: str) -> int | None:
    """Parse '1 year and 2 months', '3 weeks and 4 days', etc. -> total days."""
    parts = re.split(r"\band\b|,", text)
    total = 0
    matched_any = False
    for part in parts:
        part = part.strip()
        m = re.match(r"^(\w+)\s+(days?|weeks?|months?|years?)$", part)
        if m:
            n = _parse_number(m.group(1))
            unit = m.group(2)
            if not unit.endswith("s"):
                unit = unit + "s"
            if n is not None and unit in _UNIT_DAYS:
                total += n * _UNIT_DAYS[unit]
                matched_any = True
            else:
                return None
        else:
            return None
    return total if matched_any else None


def _parse_weekday_expression(s: str, today: date) -> date | None:
    """Handle 'next Monday', 'last Friday', 'this Wednesday', 'Monday', etc."""
    m = re.match(r"^(next|last|this)?\s*(\w+)$", s.strip())
    if not m:
        return None
    qualifier = m.group(1) or ""
    day_name = m.group(2)
    if day_name not in _WEEKDAYS:
        return None
    target_wd = _WEEKDAYS[day_name]
    current_wd = today.weekday()
    if qualifier == "last":
        delta = -((current_wd - target_wd) % 7)
        if delta == 0:
            delta = -7
    elif qualifier in ("next", "this", ""):
        delta = (target_wd - current_wd) % 7
        if delta == 0:
            delta = 7
    else:
        return None
    return today + timedelta(days=delta)


def _resolve_anchor(anchor: str, today: date) -> date | None:
    """Resolve an anchor expression (today, tomorrow, a fixed date, etc.)."""
    anchor = anchor.strip()

    # Named relative dates
    for name, delta in _NAMED_DATES.items():
        if anchor == name:
            return today + timedelta(days=delta)

    # "next <weekday>" / "last <weekday>" / "this <weekday>" / bare weekday
    m = re.match(r"^(next|last|this)?\s*(\w+)$", anchor)
    if m:
        qualifier = m.group(1) or ""
        day_name = m.group(2)
        if day_name in _WEEKDAYS:
            target_wd = _WEEKDAYS[day_name]
            current_wd = today.weekday()
            if qualifier == "next":
                delta = (target_wd - current_wd) % 7
                if delta == 0:
                    delta = 7
            elif qualifier == "last":
                delta = -((current_wd - target_wd) % 7)
                if delta == 0:
                    delta = -7
            else:
                delta = (target_wd - current_wd) % 7
                if delta == 0:
                    delta = 7
            return today + timedelta(days=delta)

    # Delegate fixed dates to dateparser
    from datetime import datetime

    settings: dict[str, object] = {
        "RELATIVE_BASE": _date_to_datetime(today),
        "PREFER_DAY_OF_MONTH": "first",
        "RETURN_AS_TIMEZONE_AWARE": False,
    }
    parsed: datetime | None = dateparser.parse(anchor, settings=settings)
    if parsed is not None:
        return parsed.date()

    return None


def _parse_relative_offset(s: str, today: date) -> date | None:
    """Handle patterns like 'N units before/after ANCHOR'."""
    # Pattern: <duration> before/after <anchor>
    m = re.match(
        r"^(.+?)\s+(before|after|from|prior to|ago)\s+(.+)$",
        s,
        re.IGNORECASE,
    )
    if m:
        duration_text = m.group(1).strip()
        direction = m.group(2).strip().lower()
        anchor_text = m.group(3).strip()

        duration_text = re.sub(r"^in\s+", "", duration_text)

        days = _parse_compound_duration(duration_text)
        if days is None:
            return None

        anchor = _resolve_anchor(anchor_text, today)
        if anchor is None:
            return None

        if direction in ("before", "prior to"):
            return anchor - timedelta(days=days)
        else:
            return anchor + timedelta(days=days)

    # "in <duration>" 
    m3 = re.match(r"^in\s+(.+)$", s)
    if m3:
        days = _parse_compound_duration(m3.group(1))
        if days is not None:
            return today + timedelta(days=days)

    # "<duration> from now/today"
    m4 = re.match(r"^(.+?)\s+from\s+(?:now|today)$", s)
    if m4:
        days = _parse_compound_duration(m4.group(1))
        if days is not None:
            return today + timedelta(days=days)

    return None
