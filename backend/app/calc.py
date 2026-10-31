"""Small date helpers shared by analytics, training and documents (standard library only)."""
import calendar
from datetime import date, timedelta


def month_key(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def month_keys(n: int, today: date) -> list[str]:
    """The last n months as YYYY-MM, oldest first, ending with the current month."""
    keys = []
    for i in range(n - 1, -1, -1):
        y, m = today.year, today.month - i
        while m <= 0:
            m += 12
            y -= 1
        keys.append(f"{y}-{m:02d}")
    return keys


def month_bounds(key: str) -> tuple[date, date]:
    y, m = (int(x) for x in key.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def month_label(key: str) -> str:
    return calendar.month_abbr[int(key.split("-")[1])]


def first_of_month_back(k: int, today: date) -> date:
    return month_bounds(month_keys(k + 1, today)[0])[0]


def weekdays(a: date, b: date) -> int:
    """Monday-Friday days from a to b, both included."""
    if b < a:
        return 0
    return sum(1 for i in range((b - a).days + 1) if (a + timedelta(days=i)).weekday() < 5)


def overlap_weekdays(start: date, end: date, a: date, b: date) -> int:
    """Working days of [start, end] that fall inside [a, b]."""
    return weekdays(max(start, a), min(end, b))


def effective_status(status: str, due: date | None, today: date) -> str:
    """A training that is still 'assigned' after its due date is overdue."""
    return "overdue" if status == "assigned" and due and due < today else status
