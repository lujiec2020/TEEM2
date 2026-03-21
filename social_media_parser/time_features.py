from __future__ import annotations
from dataclasses import dataclass


@dataclass
class EventTable:
    """
    This class provides a simplified interface for working with event data,
    including cleaner display options and time-based feature extraction.

    Attributes
    ----------
    table : Table
        Underlying datascience Table storing event data.
    """
    table: object

    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying table.

        This allows EventTable to behave like a datascience Table by
        forwarding method calls and properties.

        Parameters
        ----------
        name : str
            Name of the attribute or method being accessed.

        Returns
        -------
        object
            Attribute or method from the underlying table.
        """
        return getattr(self.table, name)

    def show(self, *args, **kwargs):
        """
        Display a simplified version of the table.

        Hides internal timestamp columns that are not necessary for
        most student-facing use cases.

        Parameters
        ----------
        *args, **kwargs
            Additional arguments passed to the underlying Table.show() method.

        Returns
        -------
        None
        """
        # Columns hidden from default display
        hidden_cols = {"timestamp_dt", "timestamp_unix"}

        # Only show user-friendly columns
        visible_cols = [col for col in self.table.labels if col not in hidden_cols]

        return self.table.select(*visible_cols).show(*args, **kwargs)

    def hide(self, *cols) -> "EventTable":
        """
        Remove specified columns from the table.

        Parameters
        ----------
        *cols : str
            Column names to remove from the table.

        Returns
        -------
        EventTable
            Updated EventTable with selected columns removed.
        """
        self.table = self.table.drop(*cols)
        return self

    def get_time_conversions(self, features, dt_col: str = "timestamp_dt") -> "EventTable":
        """
        Add time-based features derived from a datetime column.

        Supported features include:
        - "hour"
        - "weekday"
        - "month"
        - "year"
        - "date"

        Parameters
        ----------
        features : str or list of str
            One or more time features to extract.
        dt_col : str, optional
            Name of the datetime column to use (default is "timestamp_dt").

        Returns
        -------
        EventTable
            Updated EventTable with additional time feature columns.

        Raises
        ------
        ValueError
            If an unsupported feature is requested.
        """
        # Allow single feature input as string
        if isinstance(features, str):
            features = [features]

        for feature in features:
            feature = feature.lower()

            if feature == "hour":
                self.table = self.table.with_column(
                    "hour",
                    self.table.apply(lambda dt: dt.hour, dt_col)
                )

            elif feature == "weekday":
                self.table = self.table.with_column(
                    "weekday",
                    self.table.apply(lambda dt: dt.strftime("%A"), dt_col)
                )

            elif feature == "month":
                self.table = self.table.with_column(
                    "month",
                    self.table.apply(lambda dt: dt.month, dt_col)
                )

            elif feature == "year":
                self.table = self.table.with_column(
                    "year",
                    self.table.apply(lambda dt: dt.year, dt_col)
                )

            elif feature == "date":
                self.table = self.table.with_column(
                    "date",
                    self.table.apply(lambda dt: dt.date(), dt_col)
                )

            else:
                raise ValueError(
                    f"Unsupported feature: {feature}. "
                    "Use hour, weekday, month, year, or date."
                )

        return self
