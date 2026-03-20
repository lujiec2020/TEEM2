from __future__ import annotations
from dataclasses import dataclass


@dataclass
class EventTable:
    """Function for further time analysis"""
    table: object

    def __getattr__(self, name):
        return getattr(self.table, name)

    def show(self, *args, **kwargs):
        """Show a cleaner student-facing version of the table."""
        hidden_cols = {"timestamp_dt", "timestamp_unix"}
        visible_cols = [col for col in self.table.labels if col not in hidden_cols]
        return self.table.select(*visible_cols).show(*args, **kwargs)

    def hide(self, *cols) -> "EventTable":
        self.table = self.table.drop(*cols)
        return self

    def get_time_conversions(self, features, dt_col="timestamp_dt") -> "EventTable":
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
                    "Use hour, weekday, month, year, or date." # error handling
                )

        return self
