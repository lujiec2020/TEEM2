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
    # Convert timestamp and apply timezone
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

    # Build table column-by-column using the predefined schema
    for col in EVENT_COLUMNS:
        table = table.with_column(col, [row.get(col, "") for row in rows])

    return table
