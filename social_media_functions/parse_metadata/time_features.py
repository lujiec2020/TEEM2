from dataclasses import dataclass
from datetime import datetime
from datascience import Table


@dataclass
class EventTable:
    """
    Wrapper around a `datascience.Table` with convenience methods.

    This class provides helper methods for common table transformations
    while preserving immutability (methods return new EventTable instances).

    Attributes:
        table (Table): Underlying datascience table.

    Notes:
        All methods return a NEW EventTable and do not modify the original table.
    """
    table: Table

    def hide(self, *cols) -> "EventTable":
        """
        Remove specified columns from the table.

        Only columns that exist in the table will be removed; others are ignored.

        Args:
            *cols (str): Column names to remove.

        Returns:
            EventTable: New EventTable with specified columns removed.

        Example:
            >>> et.hide("timestamp", "value")
        """
        labels = set(self.table.labels)
        to_drop = [c for c in cols if c in labels]
        if not to_drop:
            return EventTable(self.table)
        return EventTable(self.table.drop(*to_drop))

    def get_time_conversions(self, features, dt_col: str = "timestamp_dt") -> "EventTable":
        """
        Add time-based feature columns derived from a datetime column.

        Supported features:
            - "hour"
            - "weekday"
            - "month"
            - "year"
            - "date"

        Args:
            features (str | list[str]): One or more feature names to generate.
            dt_col (str): Name of the datetime column to use.

        Returns:
            EventTable: New EventTable with additional time-based columns.

        Raises:
            ValueError: If an unsupported feature is requested.

        Example:
            >>> et.get_time_conversions(["hour", "weekday"])
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