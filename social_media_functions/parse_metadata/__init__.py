"""
social_media_functions

Beginner-friendly tools for parsing Instagram and TikTok data exports.
"""

from .parse_metadata import (
    parse_metadata,
    tiktok_events,
    social_media_events,
    events_by_hour,
    events_by_weekday,
    events_by_date,
    StudentInputError,
)

__all__ = [
    "StudentInputError",
    "parse_metadata",
    "tiktok_events",
    "social_media_events",
    "events_by_hour",
    "events_by_weekday",
    "events_by_date",
]
