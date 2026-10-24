"""
Cron Expression and Interval Parser.
Evaluates 5-field cron patterns, interval durations, and ISO timestamps.
"""
import re
from datetime import datetime
from typing import Optional, List


def parse_interval_seconds(interval_str: str) -> Optional[float]:
    """Parses duration strings like '30s', '5m', '2h', '1d' into seconds."""
    m = re.match(r"^(\d+)\s*([smhd])$", interval_str.strip().lower())
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return float(val * multipliers[unit])


def _match_field(field_val: int, pattern: str) -> bool:
    """Matches an integer against a cron field expression (*, */N, 1,2,3, 1-5)."""
    pattern = pattern.strip()
    if pattern == "*":
        return True
    if pattern.startswith("*/"):
        step = int(pattern[2:])
        return (field_val % step) == 0
    if "," in pattern:
        return any(_match_field(field_val, sub) for sub in pattern.split(","))
    if "-" in pattern:
        low, high = map(int, pattern.split("-"))
        return low <= field_val <= high
    return field_val == int(pattern)


def matches_cron(dt: datetime, cron_expr: str) -> bool:
    """
    Checks if a datetime matches a standard 5-field cron expression:
    minute hour day-of-month month day-of-week
    """
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return False

    min_pat, hour_pat, dom_pat, mon_pat, dow_pat = fields

    if not _match_field(dt.minute, min_pat):
        return False
    if not _match_field(dt.hour, hour_pat):
        return False
    if not _match_field(dt.day, dom_pat):
        return False
    if not _match_field(dt.month, mon_pat):
        return False
    # Python weekday(): Monday is 0, Sunday is 6. Standard cron: Sunday is 0 or 7.
    cron_dow = (dt.weekday() + 1) % 7
    if not _match_field(cron_dow, dow_pat):
        return False

    return True
