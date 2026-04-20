from dataclasses import dataclass
from datetime import datetime
from datascience import Table


@dataclass
class EventTable:
    """
    Simple wrapper around a datascience.Table with helper methods.

    IMPORTANT: Methods return NEW EventTable objects (does not mutate in place).
    """
    table: Table

    def hide(self, *cols) -> "EventTable":
        """Return a new EventTable with the given columns removed (if they exist)."""
        labels = set(self.table.labels)
        to_drop = [c for c in cols if c in labels]
        if not to_drop:
            return EventTable(self.table)
        return EventTable(self.table.drop(*to_drop))

    def get_time_conversions(self, features, dt_col: str = "timestamp_dt") -> "EventTable":
        """
        Add time-based features derived from a datetime column.

        Supported features:
          - "hour"
          - "weekday"
          - "month"
          - "year"
          - "date"

        Returns a NEW EventTable.
        """
        if isinstance(features, str):
            features = [features]

        t = self.table

        for feature in features:
            f = str(feature).lower().strip()

            if f == "hour":
                t = t.with_column("hour", t.apply(lambda dt: dt.hour if dt else None, dt_col))

            elif f == "weekday":
                t = t.with_column("weekday", t.apply(lambda dt: dt.strftime("%A") if dt else None, dt_col))

            elif f == "month":
                t = t.with_column("month", t.apply(lambda dt: dt.month if dt else None, dt_col))

            elif f == "year":
                t = t.with_column("year", t.apply(lambda dt: dt.year if dt else None, dt_col))

            elif f == "date":
                t = t.with_column("date", t.apply(lambda dt: dt.date() if dt else None, dt_col))

            else:
                raise ValueError(f"Unsupported time feature: {feature}")

        return EventTable(t)