"""
social_media_functions

Beginner-friendly tools for parsing Instagram and TikTok data exports.
"""

from .main_parser import (
    StudentInputError,
    parse_metadata,
    instagram_events,
    tiktok_events,
    social_media_events,
    events_by_hour,
    events_by_weekday,
    events_by_date,
)

__all__ = [
    "StudentInputError",
    "parse_metadata",
    "instagram_events",
    "tiktok_events",
    "social_media_events",
    "events_by_hour",
    "events_by_weekday",
    "events_by_date",
]