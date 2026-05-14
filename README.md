# nldate

A Python library for parsing natural-language date strings into `datetime.date` objects.

## Usage

```python
from datetime import date
from nldate import parse

# Absolute dates
parse("December 1st, 2025")          # date(2025, 12, 1)
parse("2025-06-15")                   # date(2025, 6, 15)

# Named relative dates
parse("today")                        # today
parse("tomorrow")                     # today + 1 day
parse("yesterday")                    # today - 1 day

# Weekday expressions
parse("next Tuesday")
parse("last Friday")

# Duration offsets
parse("in 3 days")
parse("in two weeks")
parse("three weeks from now")
parse("in 1 year and 2 months")

# Before / after anchors
parse("5 days before December 1st, 2025")
parse("1 week and 2 days after tomorrow")
parse("1 year and 2 months after yesterday")
```

## Development

```bash
uv sync
uv run pytest
uv run mypy src/ tests/
uv run ruff check src/ tests/
```
