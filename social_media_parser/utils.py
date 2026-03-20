from datetime import datetime
import pytz
from datascience import Table


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


def unix_to_local_dt(unix_ts, tz="America/New_York"):
    """Convert a UNIX timestamp to a local datetime."""
    return datetime.fromtimestamp(int(unix_ts), pytz.timezone(tz))


def format_timestamp(dt):
    """Turn a datetime into a readable timestamp string."""
    return dt.strftime("%Y-%m-%d %I:%M:%S %p %Z")


def rows_to_table(rows):
    """Convert a list of row dictionaries into a datascience Table."""
    table = Table()

    for col in EVENT_COLUMNS:
        table = table.with_column(col, [row.get(col, "") for row in rows])

    return table
