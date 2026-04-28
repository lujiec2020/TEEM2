from datetime import datetime
import pytz
from datascience import Table


"""
time_utils.py

Helper utilities for working with event-based data.

This module provides:
- Standardized event table schema
- Timestamp conversion and formatting utilities
- Conversion from raw event rows to structured tables
- Relative day indexing based on active days

All outputs are designed to integrate with `datascience.Table`.
"""


# ============================================================
# Constants
# ============================================================

EVENT_COLUMNS = [
    "object_type",
    "action_type",
    "username",
    "target",
    "value",
    "timestamp_dt",
    "timestamp",
    "timestamp_unix",
    "relative_day_index",
]
"""
list[str]: Standard column schema for all event tables.

Columns:
    object_type (str): Type of object (e.g., "video", "story").
    action_type (str): Action performed (e.g., "watch", "like").
    username (str): Actor associated with the event.
    target (str): Target content (e.g., URL, post).
    value (str): Additional metadata or text.
    timestamp_dt (datetime): Parsed datetime object.
    timestamp (str): Human-readable timestamp.
    timestamp_unix (int): Unix timestamp.
    relative_day_index (int | str): Index of active day (1-based).
"""


# ============================================================
# Timestamp utilities
# ============================================================

def unix_to_local_dt(unix_ts: int, tz: str = "America/New_York") -> datetime:
    """
    Convert a Unix timestamp to a timezone-aware datetime.

    Args:
        unix_ts (int): Unix timestamp (seconds since epoch).
        tz (str): Timezone string (default: "America/New_York").

    Returns:
        datetime: Timezone-aware datetime object.

    Raises:
        ValueError: If the timestamp cannot be converted to an integer.

    Example:
        >>> unix_to_local_dt(1700000000)
    """
    return datetime.fromtimestamp(int(unix_ts), pytz.timezone(tz))


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object into a readable timestamp string.

    Format:
        "YYYY-MM-DD HH:MM:SS AM/PM TZ"

    Args:
        dt (datetime): Datetime object to format.

    Returns:
        str: Formatted timestamp string.

    Example:
        >>> format_timestamp(datetime.now())
    """
    return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")


# ============================================================
# Table utilities
# ============================================================

def rows_to_table(rows: list) -> Table:
    """
    Convert a list of event dictionaries into a structured Table.

    Each row should follow the standard schema defined in `EVENT_COLUMNS`.
    Missing values are filled with empty strings.

    Args:
        rows (list[dict]): List of event records.

    Returns:
        Table: datascience Table with standardized columns.

    Notes:
        Column order strictly follows `EVENT_COLUMNS`.
    """
    table = Table()

    for col in EVENT_COLUMNS:
        table = table.with_column(col, [row.get(col, "") for row in rows])

    return table


# ============================================================
# Relative day indexing
# ============================================================

def index_by_active_day(rows: list) -> list:
    """
    Assign a relative day index to events based on active days.

    The first day with activity is assigned index 1, the next active day
    is index 2, and so on. Days without activity are skipped.

    Args:
        rows (list[dict]): List of event records. Each record must contain
            'timestamp_unix'.

    Returns:
        list[dict]: Updated rows with a 'relative_day_index' field added.

    Notes:
        - Rows without valid timestamps receive an empty index.
        - Indexing is based only on unique active dates.

    Example:
        >>> indexed_rows = index_by_active_day(rows)
    """
    if not rows:
        return rows

    # Step 1: Extract date from timestamp
    for row in rows:
        unix_ts = row.get("timestamp_unix")
        if unix_ts:
            row["_date"] = datetime.fromtimestamp(int(unix_ts)).date()
        else:
            row["_date"] = None

    # Step 2: Get unique active dates
    unique_dates = sorted({row["_date"] for row in rows if row["_date"] is not None})

    # Step 3: Create mapping (date → index)
    date_to_index = {date: idx + 1 for idx, date in enumerate(unique_dates)}

    # Step 4: Assign index back to rows
    for row in rows:
        date = row.get("_date")
        row["relative_day_index"] = date_to_index.get(date, "")

        # Clean up temporary field
        del row["_date"]

    return rows