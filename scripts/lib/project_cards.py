#!/usr/bin/env python3
# Purpose: sort-ready featured-project data into GitHub-safe static cards.
"""Purpose: sort-ready featured-project data into GitHub-safe static cards."""

from __future__ import annotations

from .github_api import Repository
from .render import escape_html, truncate


def _render_card(repository: Repository) -> str:
    """Render exactly one featured-project card as a safe HTML table row."""
    description = truncate(repository.description or "No description provided.")
    link = (
        f'<a href="{escape_html(repository.url)}">'
        f"<strong>{escape_html(repository.name)}</strong></a>"
    )
    return (
        "  <tr>\n"
        "    <td>\n"
        f"      {link}<br />\n"
        f"      {escape_html(description)}\n"
        "    </td>\n"
        "  </tr>"
    )


def render_project_cards(repositories: list[Repository]) -> str:
    """Render cards or the honest empty state when no public repositories exist."""
    if not repositories:
        return (
            "<div align=\"center\">\n\n"
            "No public repositories yet — check back soon\n\n"
            "</div>"
        )
    cards = "\n".join(_render_card(repository) for repository in repositories)
    return (
        "<div align=\"center\">\n\n"
        f"<table>\n<tbody>\n{cards}\n</tbody>\n</table>\n\n"
        "</div>"
    )
