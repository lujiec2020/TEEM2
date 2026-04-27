from datetime import datetime
import pytz
from datascience import Table


# Standard column schema for all event tables
EVENT_COLUMNS = [
    "object_type",
    "action_type",
    "username",
    "target",
    "value",
    "timestamp_dt",
    "timestamp",
    "timestamp_unix",
    "relative_day_index",  # Added for relative indexing
]


def unix_to_local_dt(unix_ts: int, tz: str = "America/New_York") -> datetime:
    """
    Convert a Unix timestamp to a timezone-aware datetime object.

    Parameters
    ----------
    unix_ts : int
        Unix timestamp (seconds since epoch).
    tz : str, optional
        Timezone string (default is "America/New_York").

    Returns
    -------
    datetime
        Timezone-aware datetime corresponding to the given Unix timestamp.

    Raises
    ------
    ValueError
        If the timestamp cannot be converted to an integer.
    """
    return datetime.fromtimestamp(int(unix_ts), pytz.timezone(tz))


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object into a readable string.

    Parameters
    ----------
    dt : datetime
        Datetime object to format.

    Returns
    -------
    str
        Formatted timestamp string (e.g., "2025-03-10 02:30:45 PM EST").
    """
    return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def rows_to_table(rows: list) -> Table:
    """
    Convert a list of event dictionaries into a structured Table.

    Each dictionary in the input list should follow the standard event schema
    defined in EVENT_COLUMNS. Missing values are filled with empty strings.

    Parameters
    ----------
    rows : list of dict
        List of event records where each record is a dictionary.

    Returns
    -------
    Table
        A datascience Table containing all rows with standardized columns.
    """
    table = Table()

    for col in EVENT_COLUMNS:
        table = table.with_column(col, [row.get(col, "") for row in rows])

    return table


def index_by_active_day(rows: list) -> list:
    """
    Add a relative day index to each event based only on days with activity.

    The first day with any activity is assigned index 1, the next active day
    is index 2, and so on. Days with no activity are skipped.

    Parameters
    ----------
    rows : list of dict
        List of event records. Each record must contain 'timestamp_unix'.

    Returns
    -------
    list of dict
        Updated rows with an added 'relative_day_index' field.
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

    # Step 2: Get unique active dates (skip missing)
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