"""Order records. All money is integer cents; dates are datetime.date."""
import datetime


def days_between(start: datetime.date, end: datetime.date) -> int:
    """Whole days from start to end (negative if end precedes start)."""
    return (end - start).days
