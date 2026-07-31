#!/usr/bin/env python3
# Purpose: provide shared, GitHub-safe rendering helpers for the README.
"""Purpose: provide shared, GitHub-safe rendering helpers for the README."""

from __future__ import annotations

from datetime import datetime
from html import escape


def escape_html(value: str) -> str:
    """Escape untrusted GitHub API text for safe embedding in HTML."""
    return escape(value, quote=True)


def truncate(value: str, limit: int = 100) -> str:
    """Trim text to a readable card length, adding one ellipsis if needed."""
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[:limit - 1].rstrip()}…"


def format_updated(timestamp: str) -> str:
    """Convert a GitHub timestamp to the requested human-readable month and year."""
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return parsed.strftime("Updated %b %Y")
